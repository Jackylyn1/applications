# career-kb — Jacqueline Urban's application knowledge base

A fast, exact, portable store of everything needed to generate tailored CVs and
cover letters (English & German) and to produce finished PDF applications from a
job offer.

## Files
| File | Purpose |
|------|---------|
| `profile.json` | **Source of truth.** Structured facts: personal data, skills, experience, projects, goals, role/skill map, professional profile & differentiators. Query this first. |
| `knowledge-base.md` | Same facts, human-readable. |
| `cv-standards.md` | Hard rules for CVs (ATS, content, email swap, PDF). |
| `cover-letter-standards.md` | Hard rules for cover letters (structure, tone). |
| `general-standards.md` | Project-description standard, writing principles, language matching, career positioning. |
| `communication-rules.md` | Voice/tone rules for authentic applications + cover-letter structure + the four questions every application answers. |
| `templates/CV_Template_Rezi_Dec2025.docx` | **Canonical CV layout template**, stored verbatim (byte-identical, unmodified). Use this as the visual/structural template for generated CVs. |
| `README.md` | This file. |
| `output/` | Generated applications land here. |

## How to generate an application (next step)
1. Give me a job offer — paste the text, a URL, or a PDF.
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
