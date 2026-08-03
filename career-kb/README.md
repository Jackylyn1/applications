# career-kb — [applicant]'s application knowledge base

A fast, exact, portable store of everything needed to generate tailored CVs and
cover letters (English & German) and to produce finished PDF applications from a
job offer.

This file is an **index only**. Every rule, command and convention is documented
at exactly one place; here you only find out *where* that place is.

## Files
| File | Purpose |
|------|---------|
| `profile.json` | **Source of truth — all facts/data.** Personal data, skills, experience, projects, goals, role/skill map, professional profile & differentiators. Query this first. |
| `general-standards.md` | Universal branding standards — applies to EVERY channel (CV, cover letter, LinkedIn, social). |
| `communication-rules.md` | Universal voice/tone — applies to every channel. |
| `application-standards.md` | CV & cover-letter only — fact source, language/register matching, Project Description Standard, ATS keywords, email swap, PDF output. |
| `cv-standards.md` | CV specifics — template/layout rule, section order, dates, skills bullets, summary framing, page rule. |
| `cover-letter-standards.md` | Cover-letter specifics — structure, flow, one page. |
| `linkedin-standards.md` | LinkedIn profile specifics. |
| `social-media-standards.md` | Social-media content specifics. |
| `templates/` | The canonical CV layout templates (EN + DE), stored verbatim. The ONLY layout — never design a new one. See `cv-standards.md`. |
| `tools/` | The build/render tooling — see **Tooling** below. |
| `content/` | Role/offer CV content as JSON (input to the CV build). |
| `.venv/` | Python venv with `python-docx`. Run tools as `./.venv/bin/python tools/<tool>.py`. |
| `output/base-cvs/` | The 5 target-role base CVs (EN + DE), DOCX + PDF. |
| `output/` | Job-offer applications land here. |
| `documents/` | Private source documents (Arbeitszeugnis, certificates). Not for publication. |

## Tooling
| Tool | Responsibility (documented in its own docstring) |
|------|--------------------------------------------------|
| `tools/render_application.py` | **The whole output phase, and the single definition of file naming.** Renders + verifies a CV and/or cover letter in one command. Ask it for canonical paths with `--print-paths`. |
| `tools/build_fit.py` | Builds a CV and enforces the page-length rule from `cv-standards.md`. Called by `render_application.py`. |
| `tools/build_cv.py` | Fills the stored template from a content JSON, preserving all styling. **Its docstring is the content JSON schema.** |
| `tools/ats_hygiene.py` | The single definition of ATS text hygiene (dash normalization), shared by the CV and cover-letter paths. |
| `tools/make_de_template.py` | Regenerates the German template from the English one. |

Run everything through `render_application.py`; the other tools are its
building blocks and are not meant to be invoked by hand.

## Generating an application
Use the `/generate-application` slash command
(`.claude/commands/generate-application.md`) — it is the canonical description
of the pipeline (phases, which context each subagent receives, the render
command, and the file-naming rule). Give it a job offer as text, a URL or a
PDF; you get a match summary, a tailored CV and/or cover letter as PDF, and the
editable source of each.

## Base CV templates (built 2026-07-24)
Five target roles x EN/DE = 10 CVs in `output/base-cvs/`, each role-optimized
with no job offer: `PHP-Developer`, `AI-Software-Developer`,
`Solution-Architect`, `Software-Architect`, `IT-Consultant`. When a real job
offer arrives, the pipeline starts from the closest base CV's content JSON in
`content/` and tailors it.

## Why not a vector database?
For one person's career, embeddings add an API dependency, infrastructure, and
fuzzy chunk retrieval — slower and less reliable than exact structured lookup.
`profile.json` gives complete, precise recall instantly. If this ever grows into
a large multi-document corpus, the upgrade path is: chunk these files → embed →
store in Chroma/Qdrant/pgvector. Not needed today.

## Updating
Edit `profile.json`. Never add a skill or experience that isn't genuinely
[applicant]'s. Principle: **she never lies.**
