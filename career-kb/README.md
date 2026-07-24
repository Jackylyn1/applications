# career-kb — Jacqueline Urban's application knowledge base

A fast, exact, portable store of everything needed to generate tailored CVs and
cover letters (English & German) and to produce finished PDF applications from a
job offer.

## Files
| File | Purpose |
|------|---------|
| `profile.json` | **Source of truth — all facts/data.** Personal data, skills, experience, projects, goals, role/skill map, professional profile & differentiators, engineering philosophy. Query this first. |
| `cv-standards.md` | Hard rules for CVs (ATS, content, email swap, PDF). |
| `cover-letter-standards.md` | Hard rules for cover letters (structure, tone). |
| `general-standards.md` | Project-description standard, writing principles, language matching, career positioning. |
| `communication-rules.md` | Voice/tone rules for authentic applications + cover-letter structure + the four questions every application answers. |
| `templates/CV_Template_Rezi_Dec2025.docx` | **Canonical CV layout template**, stored verbatim (byte-identical, unmodified). The ONLY layout — never design a new one. |
| `tools/build_cv.py` | Fills the template from a content JSON, preserving all styling. Its docstring is the content JSON schema. |
| `.venv/` | Python venv with `python-docx` (used by build_cv.py). Run as `./.venv/bin/python tools/build_cv.py ...`. |
| `content/` | Role/offer CV content as JSON (input to build_cv.py). |
| `README.md` | This file. |
| `output/base-cvs/` | The 5 target-role base CVs (EN + DE), DOCX + PDF. Starting point for offer-specific CVs. |
| `output/` | Job-offer applications land here. |

## Building a CV (tooling)
Layout is fixed to the template; only content changes. Workflow:
1. Write a content JSON (schema = docstring of `tools/build_cv.py`).
2. `./.venv/bin/python tools/build_cv.py --content content/<x>.json --out output/<X>.docx`
3. `soffice --headless --convert-to pdf --outdir <dir> <X>.docx` (run PDF conversions **sequentially** — LibreOffice locks its user profile under concurrency).

The generator clones the template's real paragraphs as prototypes, so fonts, colors, the right-aligned date tab, bullet list and section rules are preserved exactly. (One fix applied in code: the template's date tab stop was off-page at 20000 twips; build_cv.py re-anchors it to the right margin.)

## Base CV templates (built 2026-07-24)
Five target roles × EN/DE = 10 CVs in `output/base-cvs/`, each role-optimized with no job offer, ~2 pages:
`PHP-Developer`, `AI-Software-Developer`, `Solution-Architect`, `Software-Architect`, `IT-Consultant`.
When a real job offer arrives: start from the closest base CV's content JSON in `content/`, tailor it to the posting's keywords, rebuild.

## How to generate an application (next step)
1. Give me a job offer — paste the text, a URL, or a PDF.
   Structure: `profile.json` = all facts/data · the `*.md` files = rules only.
2. I load `profile.json` + all `*-standards.md` + `communication-rules.md`, then:
   parse the posting → match keywords against real skills → flag honest gaps →
   tailor CV + cover letter (matching the offer's language and du/Sie register) →
   embed ATS keywords naturally → render PDFs using the `templates/` layout.
3. You get: a match summary, tailored CV (PDF), tailored cover letter (PDF), and
   the editable source of each.

## PDF rendering method (this machine)
Detected tools: **Chromium 150** (primary) and **LibreOffice 24.2** (fallback).
Documents are authored as HTML+CSS (full control over a clean, ATS-friendly,
recruiter-friendly layout) and rendered headless:

```bash
chromium --headless --no-sandbox --disable-gpu \
  --print-to-pdf="output/Urban_CV_Company_en.pdf" \
  --no-pdf-header-footer \
  "career-kb/output/Urban_CV_Company_en.html"
```

ATS note: keep text as real selectable text (no text-as-image), simple single or
two-column layout, standard section headings — Chromium HTML→PDF satisfies this.

## Why not a vector database?
For one person's career, embeddings add an API dependency, infrastructure, and
fuzzy chunk retrieval — slower and less reliable than exact structured lookup.
`profile.json` gives complete, precise recall instantly. If this ever grows into
a large multi-document corpus, the upgrade path is: chunk these files → embed →
store in Chroma/Qdrant/pgvector. Not needed today.

## Updating
Edit `profile.json` (and mirror into `knowledge-base.md`). Never add a skill or
experience that isn't genuinely Jacqueline's. Principle: **she never lies.**
