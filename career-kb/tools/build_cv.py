#!/usr/bin/env python3
"""
build_cv.py — Fill the canonical Rezi DOCX template with role-optimized content.

LAYOUT IS NEVER INVENTED. This script clones the real paragraphs of
templates/CV_Template_Rezi_Dec2025.docx as prototypes (preserving fonts, sizes,
colors, the right-aligned date tab stop, and the bullet list numbering) and only
swaps the text. Content comes from a JSON file (see SCHEMA below).

Usage:
    build_cv.py --content <content.json> --out <output.docx>

CONTENT JSON SCHEMA
{
  "name": "Jacqueline Urban",
  "contact": ["Gelsenkirchen, Germany", "info@perfectseowebsite.de",
              "+49 152 13839296", "github.com/Jackylyn1", "in/jacqueline-u-92753821b"],
  "sections": [
    {"heading": "PROFESSIONAL SUMMARY", "type": "summary",
     "text": "..."},
    {"heading": "EXPERIENCE", "type": "experience", "items": [
       {"title": "AI-Assisted Web Development",
        "company": "Gastro IT GmbH",
        "right": "Mar 2025 - Present  |  Wuppertal (Remote)",
        "bullets": ["...", "..."]}
    ]},
    {"heading": "PROJECTS", "type": "experience", "items": [
       {"title": "...", "company": "...", "right": "...", "bullets": ["..."]}
    ]},
    {"heading": "EDUCATION", "type": "education", "items": [
       {"degree": "...", "detail": "..."}
    ]},
    {"heading": "SKILLS", "type": "skills", "lines": ["Backend: ...", "Frontend: ..."]}
  ]
}
Section order and headings are taken from the JSON (headings may be localized,
e.g. German). Only the four `type` values above are recognized.
"""
import argparse, copy, json, sys
from docx import Document
from docx.oxml.ns import qn

W_T = qn('w:t')
W_P = qn('w:p')
W_SECTPR = qn('w:sectPr')


def _norm(v):
    """ATS hygiene: normalize em/en dashes to a plain hyphen. A few legacy ATS
    engines (Taleo, older iCIMS) mangle '—'/'–' inconsistently, so no
    generated CV should ever contain them regardless of what the content JSON
    holds."""
    return str(v).replace('—', '-').replace('–', '-')


import re as _re
_TIMESPAN_RE = _re.compile(r'(?:19|20)\d{2}|\d{2}\.\d{4}|heute|present|lfd\.', _re.I)


def _split_timespan(right):
    """Split an experience `right` field into (timespan, rest).
    Jobs use 'timespan | location' (e.g. '03.2025 - heute | Wuppertal'); the
    leading segment matches a date pattern -> returned as the timespan, the
    remainder as location. Projects use `right` for tech/URLs (no date) -> no
    timespan, the whole string is returned as `rest`."""
    if not right:
        return '', ''
    parts = [p.strip() for p in right.split('|')]
    first = parts[0]
    if _TIMESPAN_RE.search(first) or first.lower().startswith('seit'):
        return first, ' · '.join(p for p in parts[1:] if p)
    return '', right


def get_ts(p):
    return p.findall('.//' + W_T)


W_R = qn('w:r')
W_PPR = qn('w:pPr')
W_PBDR = qn('w:pBdr')
W_NUMPR = qn('w:numPr')
W_TAB = qn('w:tab')


def _ptext(p):
    return ''.join((t.text or '') for t in p.findall('.//' + W_T))


def _has_border(p):
    ppr = p.find(W_PPR)
    return ppr is not None and ppr.find(W_PBDR) is not None


def _has_numpr(p):
    ppr = p.find(W_PPR)
    return ppr is not None and ppr.find(W_NUMPR) is not None


def _has_run_tab(p):
    return any(r.find(W_TAB) is not None for r in p.findall(W_R))


def find_prototypes(doc):
    """Locate prototype paragraphs BY STYLE, not by fixed index — the template's
    section order has been reordered before (SKILLS moved above EXPERIENCE),
    which silently broke hardcoded indices. Style markers are stable:
      * section heading  -> has a bottom border (w:pBdr)
      * bullet           -> has list numbering (w:numPr)
      * company/date line-> has a run-level tab (w:tab)  [the experience line]
      * job title        -> the paragraph immediately before that line
      * body/skill text  -> the paragraph right after the first heading (summary)
    """
    paras = [pp._p for pp in doc.paragraphs]
    heads = [i for i, e in enumerate(paras) if _has_border(e)]
    bullets = [i for i, e in enumerate(paras) if _has_numpr(e)]
    if not (heads and bullets and bullets[0] >= 2):
        raise SystemExit("Template prototypes not found (headings/bullets).")
    # An experience entry is: title, company/date line, then bullets. Anchor on
    # the first bullet: the two paragraphs just above it are the company/date
    # line and the job title. (Independent of the off-page tab, which the
    # templates no longer use.)
    hi, bi = heads[0], bullets[0]
    ci = bi - 1

    def first_empty_after(idx):
        for i in range(idx + 1, len(paras)):
            if not _ptext(paras[i]).strip() and not _has_numpr(paras[i]):
                return i
        for i, e in enumerate(paras):
            if not _ptext(e).strip() and not _has_numpr(e):
                return i
        return idx

    return {
        'name':     copy.deepcopy(paras[0]),
        'contact':  copy.deepcopy(paras[1]),
        'section':  copy.deepcopy(paras[hi]),
        'body':     copy.deepcopy(paras[hi + 1]),
        'title':    copy.deepcopy(paras[ci - 1]),
        'compdate': copy.deepcopy(paras[ci]),
        'bullet':   copy.deepcopy(paras[bi]),
        'empty':    copy.deepcopy(paras[first_empty_after(bi)]),
        'skill':    copy.deepcopy(paras[hi + 1]),
    }


def fill(proto, *values):
    """Deep-copy a prototype <w:p>; put values into its <w:t> runs in order.
    Extra runs are blanked; if fewer runs than values, the last run absorbs the
    remaining joined text."""
    p = copy.deepcopy(proto)
    ts = get_ts(p)
    if not ts:
        return p
    n = len(ts)
    for i, t in enumerate(ts):
        if i < len(values):
            if i == n - 1 and len(values) > n:
                t.text = '   '.join(_norm(v) for v in values[i:])
            else:
                t.text = _norm(values[i])
        else:
            t.text = ''
        t.set(qn('xml:space'), 'preserve')
    return p


def fill_contact(proto, items):
    """The contact paragraph has 4 icon+text slots (location, email, phone,
    profile). Map up to 4 items into those slots, preserving each icon.
    Unused trailing slots (icon + text) are removed."""
    p = copy.deepcopy(proto)
    W_R = qn('w:r')
    runs = p.findall(W_R)
    # runs alternate: [icon][text][icon][text]... find text runs (have <w:t>)
    text_run_idx = [i for i, r in enumerate(runs) if r.find(W_T) is not None]
    for slot, ti in enumerate(text_run_idx):
        t = runs[ti].find(W_T)
        if slot < len(items):
            t.text = ' ' + _norm(items[slot]) + '  '
            t.set(qn('xml:space'), 'preserve')
        else:
            # remove this text run and its preceding icon run
            p.remove(runs[ti])
            if ti - 1 >= 0 and runs[ti - 1].find(W_T) is None:
                p.remove(runs[ti - 1])
    return p


def _scale_spacing(p, scale):
    """Multiply a paragraph's before/after spacing (and line spacing, floored at
    single) by `scale`. Used to tighten the layout so a CV with a nearly-empty
    second page collapses onto one page without touching content or font size."""
    if scale == 1.0:
        return
    ppr = p.find(qn('w:pPr'))
    if ppr is None:
        return
    sp = ppr.find(qn('w:spacing'))
    if sp is None:
        return
    for attr in ('w:before', 'w:after'):
        v = sp.get(qn(attr))
        if v is not None:
            sp.set(qn(attr), str(int(int(v) * scale)))
    ln = sp.get(qn('w:line'))
    if ln is not None:
        sp.set(qn('w:line'), str(max(240, int(int(ln) * scale))))


def _drop_bullets(sections, n):
    """Remove the `n` least-important bullets and return (sections, dropped_list).
    'Least important' = trailing bullets of the later (lower-listed, i.e. older)
    experience/project entries first; never leaves an entry with zero bullets."""
    if n <= 0:
        return sections, []
    items = []
    for sec in sections:
        if sec.get('type') == 'experience':
            for it in sec['items']:
                items.append(it)
    dropped, remaining = [], n
    for it in reversed(items):
        b = it.get('bullets', [])
        while remaining > 0 and len(b) > 1:
            dropped.append((it.get('title', '?'), b.pop()))
            remaining -= 1
        if remaining <= 0:
            break
    return sections, dropped


def build(c, template, spacing_scale=1.0, drop_bullets=0):
    """Build the CV Document from content dict `c` using `template`.
    Returns (doc, dropped_bullets)."""
    import copy as _copy
    c = _copy.deepcopy(c)
    _, dropped = _drop_bullets(c['sections'], drop_bullets)

    doc = Document(template)
    proto = find_prototypes(doc)

    # The timespan now leads the job title (left-aligned), so the compdate line
    # is a plain left-aligned "company · location". Drop the run-level tab
    # character that used to right-align the date (its tab stop sat off-page at
    # 20000 twips, pushing the date off the page in the raw template).
    for r in proto['compdate'].findall(qn('w:r')):
        for tab in r.findall(qn('w:tab')):
            r.remove(tab)

    if spacing_scale != 1.0:
        for pr in proto.values():
            _scale_spacing(pr, spacing_scale)

    body = doc.element.body
    sectPr = body.find(W_SECTPR)
    for para in body.findall(W_P):
        body.remove(para)

    out = []
    out.append(fill(proto['name'], c['name']))
    out.append(fill_contact(proto['contact'], c['contact']))

    for sec in c['sections']:
        out.append(fill(proto['section'], sec['heading']))
        t = sec['type']
        if t == 'summary':
            out.append(fill(proto['body'], sec['text']))
        elif t == 'experience':
            for i, it in enumerate(sec['items']):
                # Timespan leads the title line: "03.2025 - heute | Job Title".
                # (Projects have no date in `right`, so the title is unchanged.)
                timespan, location = _split_timespan(it.get('right', ''))
                title = it['title']
                if timespan:
                    title = f"{timespan} | {title}"
                out.append(fill(proto['title'], title))
                # Second line, left-aligned: "Company · Location" (or company /
                # location / project-tech alone, whichever is present).
                comp = it.get('company', '')
                if comp and location:
                    out.append(fill(proto['compdate'], comp, ' · ' + location))
                elif comp:
                    out.append(fill(proto['compdate'], comp))
                elif location:
                    out.append(fill(proto['compdate'], location))
                for b in it.get('bullets', []):
                    out.append(fill(proto['bullet'], b))
                if i < len(sec['items']) - 1:
                    out.append(fill(proto['empty']))
        elif t == 'education':
            for i, it in enumerate(sec['items']):
                out.append(fill(proto['title'], it['degree']))
                if it.get('detail'):
                    out.append(fill(proto['body'], it['detail']))
                if i < len(sec['items']) - 1:
                    out.append(fill(proto['empty']))
        elif t == 'skills':
            lines = sec['lines']
            for i, ln in enumerate(lines):
                out.append(fill(proto['skill'], ln))
                if i < len(lines) - 1:
                    out.append(fill(proto['empty']))
        else:
            raise SystemExit(f"Unknown section type: {t}")

    for para in out:
        body.insert(list(body).index(sectPr), para)

    return doc, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--template', default=None)
    ap.add_argument('--spacing-scale', type=float, default=1.0,
                    help='Scale paragraph spacing (<1.0 tightens the layout).')
    ap.add_argument('--drop-bullets', type=int, default=0,
                    help='Drop N least-important bullets (older entries first).')
    args = ap.parse_args()

    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template = args.template or os.path.join(here, 'templates', 'CV_Template_Rezi_Dec2025.docx')

    with open(args.content, encoding='utf-8') as f:
        c = json.load(f)

    doc, dropped = build(c, template, args.spacing_scale, args.drop_bullets)
    doc.save(args.out)
    print(f"wrote {args.out}")
    for title, b in dropped:
        print(f"  dropped bullet [{title}]: {b[:70]}")


if __name__ == '__main__':
    main()
