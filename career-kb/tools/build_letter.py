#!/usr/bin/env python3
"""build_letter.py — assemble a cover-letter HTML from a content JSON + template.

WHY THIS EXISTS
    The cover-letter agent used to write the entire HTML document: doctype,
    print CSS, header, address table, date, signature - about 5.6 KB, of which
    roughly 3 KB was byte-identical boilerplate on every single run. Output is
    the most expensive token class (5x input on every model) and it is also
    100% of the wall-clock, because output is generated serially while input is
    one prefill. Paying a frontier model to retype an A4 stylesheet is the
    worst trade in the pipeline.

    So the skeleton moved here, next to the CV template, and the model now
    emits only the parts that are actual judgement: tagline, subject,
    salutation, paragraphs, closing. That is ~900 tokens instead of ~1,900.

    Same principle as page fitting and dash hygiene: if it is mechanical, it
    belongs in the renderer. The boilerplate was never a decision.

    Second reason: the old prompt pointed the agent at a previous run's letter
    in output/ as its structure reference. Those are disposable build artifacts,
    so routine cleanup deleted the reference and broke the phase. The skeleton
    now lives in templates/ - the same place as the CV templates - where nothing
    deletes it.

THE DATE IS COMPUTED HERE, NOT WRITTEN BY THE MODEL
    A letter dated by the model is a letter that can be dated wrong. Month
    names are hardcoded rather than taken from the system locale, so the output
    does not depend on how the machine happens to be configured.

CONTENT JSON
    {
      "company":         "Beispiel GmbH",            required
      "tagline":         "Softwareentwicklerin - ...",required
      "subject":         "Bewerbung als ...",         required
      "salutation":      "Hallo Beispiel-Team,",      required
      "paragraphs":      ["...", "..."],              required (>= 1)
      "addressee_lines": ["Beispiel GmbH", "HR"],     optional, default [company]
      "closing":         "Viele Gruesse"              optional, default per lang
    }

Usage:
    build_letter.py --content <letter.json> --lang de|en --out <letter.html>
"""

import argparse
import base64
import datetime
import html
import json
import os
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ats_hygiene import norm_text

KB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # career-kb/

TEMPLATES = {
    'de': os.path.join(KB, 'templates', 'coverletter_template_de.html'),
    'en': os.path.join(KB, 'templates', 'coverletter_template_en.html'),
}

SIGNATURE = os.path.join(KB, 'assets', 'signature.png')

# Hardcoded so the rendered date never depends on the machine's locale.
MONTHS = {
    'de': [
        'Januar',
        'Februar',
        'Maerz',
        'April',
        'Mai',
        'Juni',
        'Juli',
        'August',
        'September',
        'Oktober',
        'November',
        'Dezember',
    ],
    'en': [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December',
    ],
}
MONTHS['de'][2] = 'März'  # the one month name that needs a non-ASCII char

PLACE = 'Gelsenkirchen'
DEFAULT_CLOSING = {'de': 'Viele Grüße', 'en': 'Best regards'}

REQUIRED = ('company', 'tagline', 'subject', 'salutation', 'paragraphs')


def format_date(lang, today=None):
    # Local calendar day on purpose: the letter is dated where it is written.
    d = today or datetime.date.today()  # noqa: DTZ011
    month = MONTHS[lang][d.month - 1]
    if lang == 'de':
        return f'{PLACE}, {d.day}. {month} {d.year}'
    return f'{PLACE}, {d.day} {month} {d.year}'


def _clean(value):
    """Dash hygiene + HTML escaping for every model-supplied string.

    The CV path gets hygiene inside build_cv.py on each value written to the
    DOCX; the letter has no DOCX step, so it happens here - same module, same
    rules. Escaping means an ampersand in a company name cannot produce broken
    markup.
    """
    return html.escape(norm_text(str(value)), quote=False)


def signature_data_uri(path=None):
    """Inline the scanned signature so the HTML stays a single portable file.

    The letter is rendered from a scratch copy in output/, so a relative <img>
    src would break as soon as the HTML moves; a data URI cannot.

    The file is deliberately untracked: a reusable image of a handwritten
    signature does not belong in a public repository. So a fresh clone will not
    have it, and the fix is to add it - not to silently ship a letter without a
    signature, which a recruiter would read as carelessness.

    The path is resolved on call, not bound as a default, so a test can point
    SIGNATURE somewhere else.
    """
    path = path or SIGNATURE
    if not os.path.exists(path):
        raise SystemExit(
            f'error: signature image not found: {path}\n'
            f'       Scan or photograph your signature, crop it tight, save it\n'
            f'       as a PNG on white background at that path, and re-run.\n'
            f'       It stays out of git on purpose - see .gitignore.'
        )
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')


def build(content, lang, today=None):
    missing = [k for k in REQUIRED if not content.get(k)]
    if missing:
        raise SystemExit(
            f'error: cover-letter content JSON is missing required field(s): {", ".join(missing)}'
        )

    paragraphs = content['paragraphs']
    if isinstance(paragraphs, str) or not paragraphs:
        raise SystemExit('error: "paragraphs" must be a non-empty list of strings')

    addressee = content.get('addressee_lines') or [content['company']]
    body = '\n\n'.join(f'  <p>\n    {_clean(p)}\n  </p>' for p in paragraphs)

    with open(TEMPLATES[lang], encoding='utf-8') as f:
        template = string.Template(f.read())
    return template.safe_substitute(
        company=_clean(content['company']),
        tagline=_clean(content['tagline']),
        addressee='<br>\n        '.join(_clean(line) for line in addressee),
        place_date=format_date(lang, today),
        subject=_clean(content['subject']),
        salutation=_clean(content['salutation']),
        body=body,
        closing=_clean(content.get('closing') or DEFAULT_CLOSING[lang]),
        signature=signature_data_uri(),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', required=True, help='cover-letter content JSON')
    ap.add_argument('--lang', required=True, choices=['de', 'en'])
    ap.add_argument('--out', required=True, help='HTML output path')
    args = ap.parse_args()

    with open(args.content, encoding='utf-8') as f:
        content = json.load(f)

    out = build(content, args.lang)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(out)
    words = sum(len(str(p).split()) for p in content['paragraphs'])
    print(
        f'  letter assembled from template: {len(content["paragraphs"])} '
        f'paragraph(s), {words} words -> {args.out}'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
