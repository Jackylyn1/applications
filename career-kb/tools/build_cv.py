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


def get_ts(p):
    return p.findall('.//' + W_T)


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
    p = doc.paragraphs
    # Prototypes captured from the real template, then deep-copied.
    proto = {
        'name':     copy.deepcopy(p[0]._p),   # centered bold 14.5
        'contact':  copy.deepcopy(p[1]._p),   # centered 6.5, multi-run
        'section':  copy.deepcopy(p[2]._p),   # bold 10 heading
        'body':     copy.deepcopy(p[3]._p),   # 7.5 normal paragraph
        'title':    copy.deepcopy(p[5]._p),   # bold 9 job/degree title
        'compdate': copy.deepcopy(p[6]._p),   # 7.5, company \t date (right tab)
        'bullet':   copy.deepcopy(p[7]._p),   # 7.5 list item (numId=1)
        'empty':    copy.deepcopy(p[12]._p),  # spacer
        'skill':    copy.deepcopy(p[36]._p),  # 7.5 skills line
    }

    # Fix the date tab stop: the template defines a right tab at 20000 twips,
    # which is off the page (usable width ~10800 twips) and overflows in
    # LibreOffice. Re-anchor it to the actual right margin. (Design intent
    # preserved: date stays right-aligned; we only correct an off-page value.)
    sect = doc.sections[0]
    usable_twips = int((sect.page_width - sect.left_margin - sect.right_margin) / 635)
    ppr = proto['compdate'].find(qn('w:pPr'))
    if ppr is not None:
        for tab in ppr.iter(qn('w:tab')):
            tab.set(qn('w:val'), 'right')
            tab.set(qn('w:pos'), str(usable_twips))

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
                out.append(fill(proto['title'], it['title']))
                # Trailing space on company guarantees a whitespace token between
                # company and the right-tabbed date, so PDF text extraction can
                # never fuse them (e.g. "...UG" + "Jun 2021" -> "UGJun").
                comp = it.get('company', '')
                if comp:
                    comp = comp + ' '
                out.append(fill(proto['compdate'], comp, it.get('right', '')))
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
