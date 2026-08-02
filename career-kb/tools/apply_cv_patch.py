#!/usr/bin/env python3
"""apply_cv_patch.py — merge a small CV patch onto a base content JSON.

WHY THIS EXISTS
    generate-cv used to rewrite the whole content JSON (~8.3 KB / ~2.7k output
    tokens) even though a tailored CV changes maybe 15% of it: the summary, the
    order of the skill lines, and a handful of bullets. Everything else - name,
    contact, dates, company names, education - was retyped verbatim, by a
    frontier model, at output-token prices, in serial.

    Output costs 5x input and is the entire wall-clock cost of a phase, so
    retyping unchanged data is the single most expensive habit in the pipeline.
    The model now emits only the delta (~600 tokens) and the merge happens here.

    Retyping is also a correctness risk, not just a cost one: every unchanged
    field the model reproduces by hand is a field it can quietly get wrong. A
    patch cannot corrupt a date it never mentions.

    The merged result is still written to the canonical content/offer_<slug>_
    <lang>.json, so build_fit.py is untouched, the artifact stays diffable, and
    a human can read exactly what got rendered.

SECTIONS ARE ADDRESSED BY TYPE, NOT HEADING
    Headings are localised (PROFIL / PROFILE, BERUFSERFAHRUNG / EXPERIENCE), so
    keying on them would make patches language-specific. The base has two
    sections of type "experience" - jobs, then projects - so the mapping is
    (type, n-th of that type):

        summary     -> 1st type=summary
        skills      -> 1st type=skills
        experience  -> 1st type=experience   (BERUFSERFAHRUNG / EXPERIENCE)
        projects    -> 2nd type=experience   (PROJEKTE / PROJECTS)
        education   -> 1st type=education

PATCH FORMAT (every key optional)
    {
      "base":       "php-developer_de.json",      resolved under content/
      "summary":    "rewritten PROFIL text",
      "skills":     { "select": ["AI", "Backend", 2, 3] },   reorder by reference
                 or ["Backend: ...", "..."],      full replacement
      "experience": {
        "select":  ["Gastro IT", 1, "wpt-online"],   subset + order
        "rewrite": { "Gastro IT": { "bullets": ["...", "..."] } }
      },
      "projects":   { "select": [...], "rewrite": {...} },
      "education":  { "select": [...] }
    }

SELECTORS
    int -> index into the base list.
    str -> case-insensitive substring of the item's title / company / degree,
           or of the line itself for `skills`. Must match exactly one entry;
           ambiguous or unmatched fails loudly rather than silently dropping a
           job off the CV.
    "rewrite" keys resolve against the BASE list (what the model was shown),
    and are applied before "select" reorders anything.

Usage:
    apply_cv_patch.py --patch <patch.json> --out <merged.json> [--base <base.json>]
"""
import argparse, copy, json, os, sys

KB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # career-kb/
CONTENT = os.path.join(KB, 'content')

ITEM_FIELDS = ('title', 'company', 'right', 'bullets', 'degree', 'detail')
MATCH_FIELDS = ('title', 'company', 'degree')

# patch key -> (section type, which occurrence of that type)
SECTION_MAP = {
    'summary':    ('summary', 0),
    'skills':     ('skills', 0),
    'experience': ('experience', 0),
    'projects':   ('experience', 1),
    'education':  ('education', 0),
}


def find_section(doc, key):
    stype, nth = SECTION_MAP[key]
    matches = [s for s in doc.get('sections', []) if s.get('type') == stype]
    if len(matches) <= nth:
        raise SystemExit(f'error: base JSON has no section for patch key '
                         f'"{key}" (type={stype}, occurrence {nth + 1})')
    return matches[nth]


def _haystacks(item):
    """Match targets, most label-like first.

    Tier 1 is the short name a human would use; tier 2 is everything. Skill
    lines are `Category: a, b, c`, so their tier 1 is the category - otherwise a
    selector like "KI" collides with any line that merely lists a tool whose
    name happens to contain those letters ("Tailwind" contains "ai"). Trying the
    labels first keeps the common case unambiguous without giving up the ability
    to find a line by something inside it.
    """
    if isinstance(item, dict):
        labels = [str(item.get(f, '')) for f in MATCH_FIELDS]
        return labels, labels
    line = str(item)
    return [line.split(':', 1)[0]], [line]


def _label(item):
    if isinstance(item, dict):
        return item.get('title') or item.get('degree') or '?'
    return str(item)[:40]


def resolve(selector, items, key):
    """Selector -> index. Fails loudly; never guesses.

    Works for both lists of items (matched on title/company/degree) and flat
    lists of strings such as the skill lines (matched on the line itself).
    """
    if isinstance(selector, bool):
        raise SystemExit(f'error: {key}: boolean is not a valid selector')
    if isinstance(selector, int):
        if not 0 <= selector < len(items):
            raise SystemExit(f'error: {key}: index {selector} is out of range '
                             f'(base has {len(items)} entr(ies))')
        return selector
    needle = str(selector).strip().lower()
    hits = []
    for tier in (0, 1):
        hits = [i for i, it in enumerate(items)
                if any(needle in h.lower() for h in _haystacks(it)[tier])]
        if len(hits) == 1:
            return hits[0]
        if hits:
            break   # ambiguous at this tier; a broader tier cannot disambiguate
    if not hits:
        raise SystemExit(f'error: {key}: selector {selector!r} matched nothing '
                         f'in the base JSON')
    labels = ', '.join(repr(_label(items[i])) for i in hits)
    raise SystemExit(f'error: {key}: selector {selector!r} is ambiguous - '
                     f'matched {len(hits)} entries ({labels}). Use an index '
                     f'or a longer, more specific string.')


def patch_skills(section, spec, notes):
    """Skill lines: either a full replacement list, or reorder-by-reference.

    Reordering is what a tailored CV usually does to this section - the lines
    themselves are stable, only their order changes so the required stack sits
    first. Restating all nine lines to express that cost ~1,250 bytes of a real
    patch (~380 output tokens) to communicate a permutation. `select` says the
    same thing by reference.
    """
    base_lines = section.get('lines')
    if not isinstance(base_lines, list):
        raise SystemExit('error: skills: base section has no "lines" list')

    # Full replacement - still correct when the line text genuinely changes.
    if isinstance(spec, list):
        if not spec or any(not isinstance(l, str) for l in spec):
            raise SystemExit('error: "skills" must be a non-empty list of strings')
        section['lines'] = spec
        return

    if not isinstance(spec, dict):
        raise SystemExit('error: "skills" must be a list of strings, or an object '
                         'with "select" and/or "rewrite"')
    unknown = [k for k in spec if k not in ('select', 'rewrite')]
    if unknown:
        raise SystemExit(f'error: skills: unknown key(s) {unknown}. '
                         f'Allowed: ["select", "rewrite"]')

    lines = list(base_lines)
    for selector, text in (spec.get('rewrite') or {}).items():
        if not isinstance(text, str) or not text.strip():
            raise SystemExit(f'error: skills.rewrite[{selector!r}] must be a '
                             f'non-empty string')
        lines[resolve(selector, lines, 'skills.rewrite')] = text

    if 'select' in spec:
        sel = spec['select']
        if isinstance(sel, str) or not isinstance(sel, list) or not sel:
            raise SystemExit('error: skills.select must be a non-empty list')
        order = [resolve(s, lines, 'skills.select') for s in sel]
        if len(set(order)) != len(order):
            raise SystemExit('error: skills.select selects the same line twice')
        dropped = len(lines) - len(order)
        lines = [lines[i] for i in order]
        # Reordering is the normal case; dropping a whole skill category is not,
        # and it silently removes ATS keywords from the CV.
        if dropped:
            notes.append(f'skills: {dropped} skill line(s) dropped by "select" - '
                         f'check no required keyword was removed')

    section['lines'] = lines


def patch_items(section, spec, key, notes):
    items = section.get('items')
    if not isinstance(items, list):
        raise SystemExit(f'error: {key}: base section has no "items" list')
    items = copy.deepcopy(items)

    for selector, fields in (spec.get('rewrite') or {}).items():
        idx = resolve(selector, items, f'{key}.rewrite')
        if not isinstance(fields, dict):
            raise SystemExit(f'error: {key}.rewrite[{selector!r}] must be an object')
        unknown = [f for f in fields if f not in ITEM_FIELDS]
        if unknown:
            raise SystemExit(f'error: {key}.rewrite[{selector!r}]: unknown '
                             f'field(s) {unknown}. Allowed: {list(ITEM_FIELDS)}')
        if 'bullets' in fields:
            b = fields['bullets']
            if isinstance(b, str) or not isinstance(b, list) or not b:
                raise SystemExit(f'error: {key}.rewrite[{selector!r}]: "bullets" '
                                 f'must be a non-empty list of strings')
        items[idx].update(fields)

    if 'select' in spec:
        sel = spec['select']
        if isinstance(sel, str) or not isinstance(sel, list) or not sel:
            raise SystemExit(f'error: {key}.select must be a non-empty list')
        order = [resolve(s, items, f'{key}.select') for s in sel]
        if len(set(order)) != len(order):
            raise SystemExit(f'error: {key}.select selects the same item twice')
        dropped = len(items) - len(order)
        items = [items[i] for i in order]
        # Dropping a job leaves a hole in the employment history, which the CV
        # standards forbid. Projects are meant to be a curated subset, so only
        # the work-experience section gets flagged.
        if dropped and key == 'experience':
            notes.append(f'{key}: {dropped} work-experience entr(ies) dropped by '
                         f'"select" - check this does not create a CV gap')

    section['items'] = items


def apply_patch(base, patch):
    doc = copy.deepcopy(base)
    notes = []

    unknown = [k for k in patch if k not in SECTION_MAP and k != 'base']
    if unknown:
        raise SystemExit(f'error: unknown patch key(s) {unknown}. '
                         f'Allowed: {sorted(SECTION_MAP)} (+ "base")')

    if 'summary' in patch:
        text = patch['summary']
        if not isinstance(text, str) or not text.strip():
            raise SystemExit('error: "summary" must be a non-empty string')
        find_section(doc, 'summary')['text'] = text

    if 'skills' in patch:
        patch_skills(find_section(doc, 'skills'), patch['skills'], notes)

    for key in ('experience', 'projects', 'education'):
        if key not in patch:
            continue
        spec = patch[key]
        if not isinstance(spec, dict):
            raise SystemExit(f'error: "{key}" must be an object with "select" '
                             f'and/or "rewrite"')
        patch_items(find_section(doc, key), spec, key, notes)

    return doc, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--patch', required=True, help='CV patch JSON')
    ap.add_argument('--out', required=True, help='merged content JSON to write')
    ap.add_argument('--base', help='base content JSON (default: patch["base"])')
    args = ap.parse_args()

    with open(args.patch, encoding='utf-8') as f:
        patch = json.load(f)

    base_path = args.base or patch.get('base')
    if not base_path:
        raise SystemExit('error: no base given - pass --base or set "base" in '
                         'the patch JSON')
    if not os.path.isabs(base_path):
        base_path = os.path.join(CONTENT, os.path.basename(base_path))
    if not os.path.exists(base_path):
        raise SystemExit(f'error: base content JSON not found: {base_path}')

    with open(base_path, encoding='utf-8') as f:
        base = json.load(f)

    merged, notes = apply_patch(base, patch)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write('\n')

    touched = ', '.join(k for k in patch if k != 'base') or '(nothing)'
    print(f'  patch applied to {os.path.basename(base_path)}: {touched}')
    for n in notes:
        print(f'  NOTE: {n}')
    print(f'  merged CV content -> {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
