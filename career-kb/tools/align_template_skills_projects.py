#!/usr/bin/env python3
"""align_template_skills_projects.py — Make a template's PLACEHOLDER match the
generated layout for two sections the user scans:

  * SKILLS/KENNTNISSE: turn the plain skill lines into bulleted lines with a
    BOLD category label ("Backend:" bold, list normal), using the same bullet
    numbering as every other section, and delete the extra spacer paragraphs
    (so spacing is uniform).
  * PROJECT/PROJEKTE: give the project entry a timespan in front of its title
    (placeholder), like experience entries.

Style-only edits (numbering copied from a real bullet, label bolded, date
prepended); build_cv anchors its prototypes on the EXPERIENCE heading, so making
skills bullets does not disturb prototype detection. Idempotent.

Usage: python tools/align_template_skills_projects.py <template.docx> [...]
"""

import copy
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

W_PPR, W_PBDR, W_NUMPR, W_R, W_T, W_RPR, W_B = (
    qn('w:pPr'),
    qn('w:pBdr'),
    qn('w:numPr'),
    qn('w:r'),
    qn('w:t'),
    qn('w:rPr'),
    qn('w:b'),
)


def ptext(p):
    return ''.join((t.text or '') for t in p.findall('.//' + W_T))


def is_head(p):
    pr = p.find(W_PPR)
    return pr is not None and pr.find(W_PBDR) is not None


def has_num(p):
    pr = p.find(W_PPR)
    return pr is not None and pr.find(W_NUMPR) is not None


def bold_label(p):
    """Bold the 'Label:' part of a skills paragraph; keep the list normal."""
    runs = p.findall(W_R)
    first = next((r for r in runs if r.find(W_T) is not None), None)
    if first is None:
        return
    rpr0 = first.find(W_RPR)
    if rpr0 is not None and rpr0.find(W_B) is not None:
        return  # already bolded -> idempotent
    full = ''.join((r.find(W_T).text or '') for r in runs if r.find(W_T) is not None)
    if ':' not in full:  # only lines with a "Label:" part
        return
    label, rest = full.split(':', 1)
    label, rest = label + ':', rest.strip()
    t = first.find(W_T)
    t.text = label
    t.set(qn('xml:space'), 'preserve')
    rpr = first.find(W_RPR)
    if rpr is None:
        rpr = OxmlElement('w:rPr')
        first.insert(0, rpr)
    if rpr.find(W_B) is None:
        rpr.append(OxmlElement('w:b'))
    for r in runs:
        if r is not first and r.find(W_T) is not None:
            r.find(W_T).text = ''
    if rest:
        r2 = copy.deepcopy(first)
        b = r2.find(W_RPR).find(W_B)
        if b is not None:
            r2.find(W_RPR).remove(b)
        t2 = r2.find(W_T)
        t2.text = ' ' + rest
        t2.set(qn('xml:space'), 'preserve')
        first.addnext(r2)


def transform(path):
    doc = Document(path)
    paras = [p._p for p in doc.paragraphs]
    bullet_ppr = next((e.find(W_PPR) for e in paras if has_num(e)), None)
    heads = [i for i, e in enumerate(paras) if is_head(e)]

    def section(names):
        for k, i in enumerate(heads):
            if ptext(paras[i]).strip().upper() in names:
                end = heads[k + 1] if k + 1 < len(heads) else len(paras)
                return i, end
        return None, None

    n_skill, n_proj = 0, 0

    # --- SKILLS: bold-labelled bullets, drop spacers ---
    s, e = section({'SKILLS', 'KENNTNISSE'})
    if s is not None and bullet_ppr is not None:
        for i in range(s + 1, e):
            p = paras[i]
            if not ptext(p).strip():
                p.getparent().remove(p)  # spacer
                continue
            old = p.find(W_PPR)
            new = copy.deepcopy(bullet_ppr)
            p.replace(old, new) if old is not None else p.insert(0, new)
            bold_label(p)
            n_skill += 1

    # --- PROJECT: timespan in front of the entry title ---
    s, e = section({'PROJECT', 'PROJECTS', 'PROJEKTE'})
    if s is not None:
        for i in range(s + 1, e):
            if ptext(paras[i]).strip():
                ts = paras[i].findall('.//' + W_T)
                if ts and ' | ' not in (ts[0].text or ''):
                    ts[0].text = '2024 - 2025 | ' + (ts[0].text or '')
                    n_proj += 1
                break

    doc.save(path)
    print(f"{path}: {n_skill} skill line(s) bulleted, {n_proj} project timespan(s) added")


if __name__ == '__main__':
    for path in sys.argv[1:]:
        transform(path)
