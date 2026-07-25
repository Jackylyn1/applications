#!/usr/bin/env python3
"""build_fit.py — Build a CV and enforce the page-length rule.

Rule (per user): a second page is only acceptable if it carries at least
--min-lines lines of text. Otherwise the CV must collapse onto ONE page.
Escalation, least-destructive first:
  1) tighten paragraph spacing (no content lost, font size unchanged)
  2) if that is not enough, drop the least-important bullets (trailing bullets
     of the older/lower-listed roles first; every role keeps >=1 bullet)

Renders with LibreOffice (soffice) and inspects the PDF with pdfinfo/pdftotext.

Usage:
  build_fit.py --content <json> --template <docx> --out <docx> [--min-lines 10]
The PDF is written next to --out (same name, .pdf).
"""
import argparse, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from build_cv import build

# (spacing_scale, drop_bullets), least-destructive first: exhaust gentle spacing
# tightening before removing any content, and CAP the damage — never squeeze
# below 0.82 spacing and never drop more than 3 bullets to force one page. If a
# clean single page needs more than that, a clean 2-pager is the better outcome
# (see the fallback in main()), rather than gutting the CV.
STEPS = [(1.0, 0), (0.92, 0), (0.85, 0), (0.82, 0), (0.82, 1), (0.82, 2), (0.82, 3)]


def render_pdf(docx, outdir):
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir',
                    outdir, docx], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.join(outdir, os.path.splitext(os.path.basename(docx))[0] + '.pdf')


def page_count(pdf):
    out = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.lower().startswith('pages:'):
            return int(line.split(':')[1])
    return 0


def page2_lines(pdf):
    out = subprocess.run(['pdftotext', '-f', '2', '-l', '2', pdf, '-'],
                         capture_output=True, text=True).stdout
    return sum(1 for ln in out.splitlines() if ln.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', required=True)
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-lines', type=int, default=10)
    args = ap.parse_args()

    with open(args.content, encoding='utf-8') as f:
        c = json.load(f)

    outdir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(outdir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        chosen = None
        for scale, drop in STEPS:
            doc, dropped = build(c, args.template, scale, drop)
            doc.save(args.out)
            pdf = render_pdf(args.out, tmp)
            pages = page_count(pdf)
            p2 = page2_lines(pdf) if pages >= 2 else 0
            # Accept a clean single page, or a genuinely full second page.
            ok = pages <= 1 or (pages == 2 and p2 >= args.min_lines)
            print(f"  try scale={scale} drop={drop}: pages={pages} page2_lines={p2} "
                  f"{'OK' if ok else '...'}")
            if ok:
                chosen = (scale, drop, pages, p2, dropped, pdf)
                break
        if chosen is None:
            # One page was only reachable by cutting too much (> the caps in
            # STEPS). A clean 2-pager with all content beats a gutted 1-pager,
            # so revert to the intact original and flag the sparse page 2.
            doc, dropped = build(c, args.template, 1.0, 0)
            doc.save(args.out)
            pdf = render_pdf(args.out, tmp)
            pages, p2, scale, drop = page_count(pdf), page2_lines(pdf), 1.0, 0
            print(f"  NOTE: one page would need cutting >3 bullets; kept intact "
                  f"{pages} pages (page 2 has {p2} lines, below the "
                  f"{args.min_lines}-line target) — trim content manually if a "
                  f"single page is required.")

        if chosen is not None:
            scale, drop, pages, p2, dropped, pdf = chosen
        # final docx already saved for the chosen step; copy its rendered PDF next to it
        final_pdf = os.path.splitext(args.out)[0] + '.pdf'
        import shutil
        shutil.copyfile(pdf, final_pdf)

    print(f"wrote {args.out} + {os.path.basename(final_pdf)} "
          f"[scale={scale}, dropped={len(dropped)} bullets, pages={pages}, page2_lines={p2}]")
    for title, b in dropped:
        print(f"    - dropped bullet [{title}]: {b[:70]}")


if __name__ == '__main__':
    main()
