#!/usr/bin/env python3
"""render_application.py — render and verify a generated application, in one step.

This is the whole output phase. It exists so the pipeline's final step is a
deterministic script rather than an agent issuing a dozen shell commands: the
actual work takes about a second, and every check below is mechanical.

It is also the SINGLE DEFINITION OF FILE NAMING for the pipeline. Nothing else
- no agent prompt, no standards file - may spell out an output filename; ask
this script instead:

    render_application.py --company <slug> --lang de --print-paths

NAMING CONVENTION (defined once, here)
    company slug         always lowercase kebab-case (enforced, not assumed)
    CV patch JSON        content/patch_<slug>_<lang>.json      <- model writes
    CV content JSON      content/offer_<slug>_<lang>.json      <- merged here
    letter content JSON  output/coverletter_<slug>_<lang>.json <- model writes
    cover-letter source  output/coverletter_<slug>_<lang>.html <- assembled here
    CV output            output/<Surname>_CV_<slug>_<lang>.docx  (+ .pdf)
    cover-letter output  output/<Surname>_CoverLetter_<slug>_<lang>.pdf
    The surname comes from profile.json and its `_CV_` / `_CoverLetter_`
    prefixes stay capitalized because a recruiter sees those filenames; the
    slug is always lowercase.

THE MODEL WRITES DELTAS, THIS SCRIPT WRITES DOCUMENTS
    Both generation phases emit only what is a judgement call, and this script
    assembles the rest:
      * the CV patch is merged onto its base by tools/apply_cv_patch.py, and
        the merged content JSON is still written to the canonical path, so
        build_fit.py is unchanged and the result stays diffable;
      * the letter content JSON is poured into templates/coverletter_template_
        <lang>.html by tools/build_letter.py, which also computes the date.
    Retyping unchanged boilerplate cost ~3.5k output tokens per run - the most
    expensive token class, and the whole of the serial wall-clock - so it moved
    into code. Same rule as page fitting and dash hygiene: mechanical work is
    the renderer's job.

Rendering: the CV goes through tools/build_fit.py (template fill + the
page-length rule). The cover letter is rendered by headless Chromium, with
LibreOffice as the fallback. Conversions run sequentially - LibreOffice locks
its user profile under concurrency.

Usage:
    render_application.py --company <slug> --lang de|en
                          [--patch <cv_patch.json>] [--content <cv.json>]
                          [--letter <letter.json>] [--cover-letter <letter.html>]
                          [--print-paths]
With no input flags the canonical paths above are used when they exist.
Exits non-zero if any verification fails.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profile_digest import applicant_name

from apply_cv_patch import apply_patch
from ats_hygiene import count_violations, norm_file
from build_letter import build as build_letter

KB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # career-kb/
TOOLS = os.path.join(KB, 'tools')
OUTPUT = os.path.join(KB, 'output')
CONTENT = os.path.join(KB, 'content')
# In the container the venv lives outside the bind mount, so it is passed in.
VENV_PY = os.environ.get('CAREER_KB_PYTHON') or os.path.join(KB, '.venv', 'bin', 'python')

TEMPLATES = {
    'de': os.path.join(KB, 'templates', 'CV_Template_Rezi_DE_Dec2025.docx'),
    'en': os.path.join(KB, 'templates', 'CV_Template_Rezi_Dec2025.docx'),
}

APPLICATION_EMAIL = 'info@perfectseowebsite.de'
# The private address must never reach a generated document - but writing it in
# here would publish, in a public repository, the exact string the check exists
# to protect. It is read from the environment instead, and when it is unset the
# check reports SKIP rather than OK, so an unset variable cannot pass for a
# clean run.
PERSONAL_EMAIL = os.environ.get('CAREER_KB_PERSONAL_EMAIL', '')


# ---------------------------------------------------------------- naming ----


def normalize_slug(company):
    """Company slugs are always lowercase kebab-case. Enforced, not trusted."""
    slug = re.sub(r'[^a-z0-9]+', '-', str(company).lower()).strip('-')
    if not slug:
        raise SystemExit('error: --company produced an empty slug')
    return slug


def paths_for(company, lang):
    slug = normalize_slug(company)
    surname = applicant_name().split()[-1]
    return {
        'slug': slug,
        'cv_patch': os.path.join(CONTENT, f'patch_{slug}_{lang}.json'),
        'cv_content': os.path.join(CONTENT, f'offer_{slug}_{lang}.json'),
        'cl_content': os.path.join(OUTPUT, f'coverletter_{slug}_{lang}.json'),
        'cl_source': os.path.join(OUTPUT, f'coverletter_{slug}_{lang}.html'),
        'cv_docx': os.path.join(OUTPUT, f'{surname}_CV_{slug}_{lang}.docx'),
        'cv_pdf': os.path.join(OUTPUT, f'{surname}_CV_{slug}_{lang}.pdf'),
        'cl_pdf': os.path.join(OUTPUT, f'{surname}_CoverLetter_{slug}_{lang}.pdf'),
    }


# --------------------------------------------------------------- helpers ----


def pdf_pages(pdf):
    out = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True, check=False).stdout
    for line in out.splitlines():
        if line.lower().startswith('pages:'):
            return int(line.split(':')[1])
    return 0


def pdf_text(pdf):
    return subprocess.run(
        ['pdftotext', pdf, '-'], capture_output=True, text=True, check=False
    ).stdout


# -------------------------------------------------------------- assembling --


def merge_cv_patch(patch_path, content_out, base_override=None):
    """Merge the model's CV patch onto its base and write the content JSON."""
    with open(patch_path, encoding='utf-8') as f:
        patch = json.load(f)

    base_path = base_override or patch.get('base')
    if not base_path:
        raise SystemExit(
            f'error: {patch_path} has no "base" - the patch must '
            f'name the base content JSON it applies to'
        )
    if not os.path.isabs(base_path):
        base_path = os.path.join(CONTENT, os.path.basename(base_path))
    if not os.path.exists(base_path):
        raise SystemExit(f'error: base content JSON not found: {base_path}')

    with open(base_path, encoding='utf-8') as f:
        base = json.load(f)

    merged, notes = apply_patch(base, patch)
    with open(content_out, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write('\n')

    touched = ', '.join(k for k in patch if k != 'base') or '(nothing)'
    print(f'  patch applied to {os.path.basename(base_path)}: {touched}')
    for n in notes:
        print(f'  NOTE: {n}')
    return content_out


def assemble_letter(content_path, lang, html_out):
    """Pour the model's letter content into the protected A4 template."""
    with open(content_path, encoding='utf-8') as f:
        content = json.load(f)
    html_text = build_letter(content, lang)
    with open(html_out, 'w', encoding='utf-8') as f:
        f.write(html_text)
    words = sum(len(str(p).split()) for p in content['paragraphs'])
    print(
        f'  letter assembled from template: {len(content["paragraphs"])} '
        f'paragraph(s), {words} words'
    )
    return html_out


# --------------------------------------------------------------- rendering --


def render_cv(content, lang, docx_out):
    """Delegate to build_fit.py so the page-length rule lives in one place."""
    template = TEMPLATES[lang]
    proc = subprocess.run(
        [
            VENV_PY,
            os.path.join(TOOLS, 'build_fit.py'),
            '--content',
            content,
            '--template',
            template,
            '--out',
            docx_out,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f'error: build_fit.py failed for {content}')
    return os.path.splitext(docx_out)[0] + '.pdf'


# Least-destructive first, and CAPPED - same philosophy as build_fit.py's
# spacing escalation for the CV. Below 0.88 a letter starts looking cramped, so
# we stop and let the run fail loudly rather than shipping something ugly.
FIT_STEPS = [1.0, 0.97, 0.94, 0.91, 0.88]


def _with_zoom(html_text, zoom):
    """Inject a print-time scale override without touching the source file."""
    if zoom >= 1.0:
        return html_text
    override = f'<style>body{{zoom:{zoom};}}</style>'
    if '</head>' in html_text:
        return html_text.replace('</head>', override + '</head>', 1)
    return override + html_text


def fit_cover_letter(html, pdf_out):
    """Render the cover letter and GUARANTEE one page, or fail loudly.

    Before this existed, fitting was the agent's job: it wrote the letter,
    page-checked, and edited it down - seven Edit calls in one measured run,
    each costing a full context re-read (~44k tokens). That loop was ~300k read
    tokens to shorten one page of text. Scaling is deterministic, so it belongs
    in code; the model's job is the content, not the millimetres.
    """
    with open(html, encoding='utf-8') as f:
        source = f.read()
    scratch = os.path.join(OUTPUT, '.fit.html')
    try:
        for zoom in FIT_STEPS:
            with open(scratch, 'w', encoding='utf-8') as f:
                f.write(_with_zoom(source, zoom))
            render_cover_letter(scratch, pdf_out)
            pages = pdf_pages(pdf_out)
            print(f'  fit: zoom={zoom} -> {pages} page(s)' + ('  OK' if pages <= 1 else ' ...'))
            if pages <= 1:
                return pdf_out
        print(
            f'  NOTE: still {pages} pages at the {FIT_STEPS[-1]} scale cap - '
            f'the letter is too long to fit by scaling; shorten the text.'
        )
        return pdf_out
    finally:
        if os.path.exists(scratch):
            os.remove(scratch)


def render_cover_letter(html, pdf_out):
    """Headless Chromium, LibreOffice as fallback.

    The output path must stay inside the project: snap Chromium cannot write
    to /tmp.
    """
    chromium = subprocess.run(
        [
            'chromium',
            '--headless=new',
            '--no-sandbox',
            '--disable-gpu',
            f'--print-to-pdf={pdf_out}',
            '--no-pdf-header-footer',
            html,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if chromium.returncode == 0 and os.path.exists(pdf_out):
        print('  cover letter rendered with Chromium')
        return pdf_out

    print('  Chromium failed, falling back to LibreOffice')
    subprocess.run(
        [
            'soffice',
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            os.path.dirname(pdf_out),
            html,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    produced = os.path.join(
        os.path.dirname(pdf_out), os.path.splitext(os.path.basename(html))[0] + '.pdf'
    )
    if produced != pdf_out:
        shutil.move(produced, pdf_out)
    return pdf_out


# ------------------------------------------------------------ verification --


def verify(pdf, label, expect_pages=None):
    """Mechanical checks every generated document must pass.

    A check is (message, ok), where ok is True, False, or None for "could not be
    run" - see PERSONAL_EMAIL.
    """
    checks = []
    ok_exists = os.path.exists(pdf) and os.path.getsize(pdf) > 0
    checks.append((f'{label}: file exists and is non-empty', ok_exists))
    if not ok_exists:
        return checks

    pages = pdf_pages(pdf)
    if expect_pages is not None:
        checks.append((f'{label}: {pages} page(s), expected {expect_pages}', pages == expect_pages))
    else:
        checks.append((f'{label}: {pages} page(s)', pages >= 1))

    text = pdf_text(pdf)
    checks.append(
        (f'{label}: text is selectable ({len(text.split())} words)', len(text.strip()) > 0)
    )
    checks.append((f'{label}: application email present', APPLICATION_EMAIL in text))
    if PERSONAL_EMAIL:
        checks.append((f'{label}: personal email absent', PERSONAL_EMAIL not in text))
    else:
        checks.append((f'{label}: personal email absent (CAREER_KB_PERSONAL_EMAIL unset)', None))
    dashes = count_violations(text)
    checks.append((f'{label}: no em/en dashes ({dashes} found)', dashes == 0))
    return checks


# -------------------------------------------------------------------- main --


def resolve_inputs(args, p):
    """Pick the inputs to work from, most-processed first.

    An explicitly passed pre-built artifact wins, then the model's delta, then
    whatever sits at the canonical path. Returns (cv_patch, cv_json, cl_json,
    cl_html), any of which may be None.
    """

    def pick(explicit, canonical):
        return explicit or (canonical if os.path.exists(canonical) else None)

    inputs = (
        pick(args.patch, p['cv_patch']),
        pick(args.content, p['cv_content']),
        pick(args.letter, p['cl_content']),
        pick(args.cover_letter, p['cl_source']),
    )
    if not any(inputs):
        raise SystemExit(
            'error: nothing to render - no patch, content or letter '
            'JSON found at the canonical paths, and none passed'
        )
    return inputs


STATUS = {True: 'OK', False: 'FAIL', None: 'SKIP'}


def report(checks, produced):
    """Print the verification table and the artifact list; return the exit code."""
    print('\nVERIFICATION')
    failed = skipped = 0
    for msg, ok in checks:
        print(f'  [{STATUS[ok]}] {msg}')
        failed += 1 if ok is False else 0
        skipped += 1 if ok is None else 0

    print('\nPRODUCED')
    for f in produced:
        print(f'  {f}')

    if failed:
        print(f'\n{failed} check(s) FAILED')
        return 1
    passed = len(checks) - skipped
    print(f'\nAll {passed} checks passed.' + (f' {skipped} skipped.' if skipped else ''))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--company', help='company slug (lowercased)')
    ap.add_argument('--lang', choices=['de', 'en'])
    ap.add_argument('--patch', help='CV patch JSON (default: canonical path)')
    ap.add_argument(
        '--base', help='base content JSON for the patch (default: the patch\'s own "base" field)'
    )
    ap.add_argument(
        '--content',
        help='pre-merged CV content JSON - skips the patch step (default: canonical path)',
    )
    ap.add_argument('--letter', help='cover-letter content JSON (default: canonical path)')
    ap.add_argument(
        '--cover-letter', help='pre-assembled cover-letter HTML - skips the template step'
    )
    ap.add_argument('--print-paths', action='store_true', help='print the canonical paths and exit')
    args = ap.parse_args()

    if not (args.company and args.lang):
        raise SystemExit('error: --company and --lang are required')

    p = paths_for(args.company, args.lang)

    if args.print_paths:
        for k, v in p.items():
            print(f'{k}\t{v}')
        return 0

    cv_patch, cv_json, cl_json, cl_html = resolve_inputs(args, p)

    os.makedirs(OUTPUT, exist_ok=True)
    produced, checks = [], []

    # Assemble before rendering: a malformed delta should fail here, before any
    # Chromium or LibreOffice process is started.
    if cv_patch and not args.content:
        print(f'CV patch: {cv_patch}')
        cv_json = merge_cv_patch(cv_patch, p['cv_content'], args.base)
    if cl_json and not args.cover_letter:
        print(f'Letter content: {cl_json}')
        cl_html = assemble_letter(cl_json, args.lang, p['cl_source'])

    # Sequential on purpose: LibreOffice locks its user profile.
    if cv_json:
        print(f'CV: {cv_json}')
        # The CV path applies dash hygiene inside build_cv.py, on every value
        # written into the DOCX - see ats_hygiene.norm_text.
        cv_pdf = render_cv(cv_json, args.lang, p['cv_docx'])
        produced += [p['cv_docx'], cv_pdf]
        checks += verify(cv_pdf, 'CV')

    if cl_html:
        print(f'Cover letter: {cl_html}')
        # The cover-letter path has no DOCX build step, so hygiene is applied
        # to the source here - same rules, same module.
        fixed = norm_file(cl_html)
        if fixed:
            print(f'  ats_hygiene: normalized {fixed} dash(es) in the HTML')
        cl_pdf = fit_cover_letter(cl_html, p['cl_pdf'])
        produced += [cl_html, cl_pdf]
        checks += verify(cl_pdf, 'Cover letter', expect_pages=1)

    return report(checks, produced)


if __name__ == '__main__':
    sys.exit(main())
