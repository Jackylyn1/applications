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
    CV content JSON      content/offer_<slug>_<lang>.json
    cover-letter source  output/coverletter_<slug>_<lang>.html
    CV output            output/Urban_CV_<slug>_<lang>.docx  (+ .pdf)
    cover-letter output  output/Urban_CoverLetter_<slug>_<lang>.pdf
    The `Urban_CV_` / `Urban_CoverLetter_` prefixes stay capitalized because a
    recruiter sees those filenames; the slug is always lowercase.

Rendering: the CV goes through tools/build_fit.py (template fill + the
page-length rule). The cover letter is rendered by headless Chromium, with
LibreOffice as the fallback. Conversions run sequentially - LibreOffice locks
its user profile under concurrency.

Usage:
    render_application.py --company <slug> --lang de|en
                          [--content <cv.json>] [--cover-letter <letter.html>]
                          [--print-paths]
At least one of --content / --cover-letter is required (unless --print-paths).
Exits non-zero if any verification fails.
"""
import argparse, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ats_hygiene import norm_file, count_violations

KB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # career-kb/
TOOLS = os.path.join(KB, 'tools')
OUTPUT = os.path.join(KB, 'output')
CONTENT = os.path.join(KB, 'content')
VENV_PY = os.path.join(KB, '.venv', 'bin', 'python')

TEMPLATES = {
    'de': os.path.join(KB, 'templates', 'CV_Template_Rezi_DE_Dec2025.docx'),
    'en': os.path.join(KB, 'templates', 'CV_Template_Rezi_Dec2025.docx'),
}

APPLICATION_EMAIL = 'info@perfectseowebsite.de'
PERSONAL_EMAIL = 'diejacky@gmx.net'   # must never reach a generated document


# ---------------------------------------------------------------- naming ----

def normalize_slug(company):
    """Company slugs are always lowercase kebab-case. Enforced, not trusted."""
    slug = re.sub(r'[^a-z0-9]+', '-', str(company).lower()).strip('-')
    if not slug:
        raise SystemExit('error: --company produced an empty slug')
    return slug


def paths_for(company, lang):
    slug = normalize_slug(company)
    return {
        'slug': slug,
        'cv_content': os.path.join(CONTENT, f'offer_{slug}_{lang}.json'),
        'cl_source': os.path.join(OUTPUT, f'coverletter_{slug}_{lang}.html'),
        'cv_docx': os.path.join(OUTPUT, f'Urban_CV_{slug}_{lang}.docx'),
        'cv_pdf': os.path.join(OUTPUT, f'Urban_CV_{slug}_{lang}.pdf'),
        'cl_pdf': os.path.join(OUTPUT, f'Urban_CoverLetter_{slug}_{lang}.pdf'),
    }


# --------------------------------------------------------------- helpers ----

def pdf_pages(pdf):
    out = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.lower().startswith('pages:'):
            return int(line.split(':')[1])
    return 0


def pdf_text(pdf):
    return subprocess.run(['pdftotext', pdf, '-'],
                          capture_output=True, text=True).stdout


# --------------------------------------------------------------- rendering --

def render_cv(content, lang, docx_out):
    """Delegate to build_fit.py so the page-length rule lives in one place."""
    template = TEMPLATES[lang]
    proc = subprocess.run(
        [VENV_PY, os.path.join(TOOLS, 'build_fit.py'),
         '--content', content, '--template', template, '--out', docx_out],
        capture_output=True, text=True)
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
    source = open(html, encoding='utf-8').read()
    scratch = os.path.join(OUTPUT, '.fit.html')
    try:
        for zoom in FIT_STEPS:
            with open(scratch, 'w', encoding='utf-8') as f:
                f.write(_with_zoom(source, zoom))
            render_cover_letter(scratch, pdf_out)
            pages = pdf_pages(pdf_out)
            print(f'  fit: zoom={zoom} -> {pages} page(s)'
                  + ('  OK' if pages <= 1 else ' ...'))
            if pages <= 1:
                return pdf_out
        print(f'  NOTE: still {pages} pages at the {FIT_STEPS[-1]} scale cap - '
              f'the letter is too long to fit by scaling; shorten the text.')
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
        ['chromium', '--headless=new', '--no-sandbox', '--disable-gpu',
         f'--print-to-pdf={pdf_out}', '--no-pdf-header-footer', html],
        capture_output=True, text=True)
    if chromium.returncode == 0 and os.path.exists(pdf_out):
        print(f'  cover letter rendered with Chromium')
        return pdf_out

    print('  Chromium failed, falling back to LibreOffice')
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(pdf_out), html],
                   check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    produced = os.path.join(os.path.dirname(pdf_out),
                            os.path.splitext(os.path.basename(html))[0] + '.pdf')
    if produced != pdf_out:
        shutil.move(produced, pdf_out)
    return pdf_out


# ------------------------------------------------------------ verification --

def verify(pdf, label, expect_pages=None):
    """Mechanical checks every generated document must pass."""
    checks = []
    ok_exists = os.path.exists(pdf) and os.path.getsize(pdf) > 0
    checks.append((f'{label}: file exists and is non-empty', ok_exists))
    if not ok_exists:
        return checks

    pages = pdf_pages(pdf)
    if expect_pages is not None:
        checks.append((f'{label}: {pages} page(s), expected {expect_pages}',
                       pages == expect_pages))
    else:
        checks.append((f'{label}: {pages} page(s)', pages >= 1))

    text = pdf_text(pdf)
    checks.append((f'{label}: text is selectable ({len(text.split())} words)',
                   len(text.strip()) > 0))
    checks.append((f'{label}: application email present',
                   APPLICATION_EMAIL in text))
    checks.append((f'{label}: personal email absent',
                   PERSONAL_EMAIL not in text))
    dashes = count_violations(text)
    checks.append((f'{label}: no em/en dashes ({dashes} found)', dashes == 0))
    return checks


# -------------------------------------------------------------------- main --

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--company', help='company slug (lowercased)')
    ap.add_argument('--lang', choices=['de', 'en'])
    ap.add_argument('--content', help='CV content JSON (default: canonical path)')
    ap.add_argument('--cover-letter', help='cover-letter HTML (default: canonical path)')
    ap.add_argument('--print-paths', action='store_true',
                    help='print the canonical paths and exit')
    ap.add_argument('--page-check', metavar='HTML',
                    help='render HTML to a scratch PDF, print its page count, '
                         'and delete it (for the cover-letter agent to verify '
                         'one page without inventing its own render command)')
    args = ap.parse_args()

    if args.page_check:
        os.makedirs(OUTPUT, exist_ok=True)
        scratch = os.path.join(OUTPUT, '.pagecheck.pdf')
        render_cover_letter(args.page_check, scratch)
        print(f'pages: {pdf_pages(scratch)}')
        os.remove(scratch)
        return 0

    if not (args.company and args.lang):
        raise SystemExit('error: --company and --lang are required')

    p = paths_for(args.company, args.lang)

    if args.print_paths:
        for k, v in p.items():
            print(f'{k}\t{v}')
        return 0

    cv_json = args.content or (p['cv_content'] if os.path.exists(p['cv_content']) else None)
    cl_html = args.cover_letter or (p['cl_source'] if os.path.exists(p['cl_source']) else None)
    if not cv_json and not cl_html:
        raise SystemExit('error: nothing to render - pass --content and/or --cover-letter')

    os.makedirs(OUTPUT, exist_ok=True)
    produced, checks = [], []

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

    print('\nVERIFICATION')
    failed = 0
    for msg, ok in checks:
        print(f'  [{"OK" if ok else "FAIL"}] {msg}')
        failed += 0 if ok else 1

    print('\nPRODUCED')
    for f in produced:
        print(f'  {f}')

    if failed:
        print(f'\n{failed} check(s) FAILED')
        return 1
    print(f'\nAll {len(checks)} checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
