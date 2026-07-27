#!/usr/bin/env python3
"""ats_hygiene.py — the single definition of ATS text hygiene.

Every generated application document (CV *and* cover letter) passes through
here, so the rules live in exactly one place.

Rule: em/en dashes are normalized to a plain hyphen. A few legacy ATS engines
(Taleo, older iCIMS) mangle '-'/'-' inconsistently, so no generated document
should contain them regardless of what the source content holds.

Used by:
  - tools/build_cv.py      -> norm_text() on every value written into the DOCX
  - tools/render_application.py -> norm_file() on the cover-letter HTML
  - CLI: ats_hygiene.py <file>...   (normalize files in place)
"""
import sys

# Literal characters plus the HTML entities that render as them, so the rule
# holds for HTML sources as well as plain DOCX text.
REPLACEMENTS = {
    '—': '-',   # em dash
    '–': '-',   # en dash
    '&mdash;': '-',
    '&ndash;': '-',
    '&#8212;': '-',
    '&#8211;': '-',
}


def norm_text(value):
    """Return `value` as a string with every disallowed dash replaced."""
    text = str(value)
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def count_violations(text):
    """How many disallowed sequences `text` still contains."""
    return sum(text.count(bad) for bad in REPLACEMENTS)


def norm_file(path):
    """Normalize a file in place. Returns the number of replacements made."""
    with open(path, encoding='utf-8') as f:
        original = f.read()
    fixed = norm_text(original)
    if fixed != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fixed)
    return count_violations(original)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for path in sys.argv[1:]:
        n = norm_file(path)
        print(f"ats_hygiene: {path} - {n} dash(es) normalized")
    return 0


if __name__ == '__main__':
    sys.exit(main())
