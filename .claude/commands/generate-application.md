---
description: Generate a tailored, ATS-optimized CV and/or cover letter from a job offer by orchestrating the preparation and generate-documents subagents.
model: sonnet
---
# /generate-application — application pipeline (orchestrator)
You orchestrate. Never parse or write CV/cover-letter content yourself; delegate via the Task tool. Only this command references context files and subagents.

## Context injection: paths, never contents
Inject the absolute paths below and let the subagent read them. Never read these files yourself and never paste their contents into a prompt.

Inject the fact base as the phase-scoped digest, never as `profile.json`. Digests are gitignored, so step 3 rebuilds them first.

- **Main (every phase):**
  - `career-kb/.digest/profile_<phase>.json` — facts (`<phase>` = `preparation` | `documents`)
  - `career-kb/general-standards.md` — branding
  - `career-kb/communication-rules.md` — voice
  - `career-kb/sound-like-human-standards.md`
  - `career-kb/application-standards.md`
- **generate-documents also gets:**
  - `career-kb/cv-standards.md`
  - `career-kb/cover-letter-standards.md`
  - `career-kb/examples/coverletter_<slug>_<lang>.json` — the letter's tone/length reference. Inject the `.json`, never the `.html`. The file is not in git; on a fresh clone, skip it and rely on the cover-letter standards.

Pass every path a phase needs. `generate-documents` has no `Bash` tool and cannot look one up.

## File naming
`render_application.py` is the single source of truth. Resolve output paths with:
```sh
career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en> --print-paths
```
Run it after `preparation`, since the slug comes from the offer. Pass the resulting absolute paths to `generate-documents`. Never hardcode filenames.

## The generator emits deltas, the renderer emits documents
`generate-documents` writes two small files, never a finished document:
- **`cv_patch`** (`content/patch_<slug>_<lang>.json`) — changed CV fields only. The renderer merges it onto the base and writes `cv_content`.
- **`cl_content`** (`output/coverletter_<slug>_<lang>.json`) — tagline, subject, salutation, paragraphs. The renderer pours it into `templates/coverletter_template_<lang>.html`, computes the date and writes `cl_source`.

Inject those two paths, never `cv_content` / `cl_source`.

## Subagents
`preparation` (Opus) → `generate-documents` (Sonnet). CV and letter are one agent, not two. Rendering is not a subagent; you run it in step 6.

## Asking
Ask only when guessing would be unsafe or waste work.
- Never ask for language or register — they come from `preparation`.
- Never ask for company slug, filenames or paths — resolve them with `--print-paths`.

## Steps
1. Ask for the job offer.
2. Ask whether to generate both documents, CV only, or cover letter only.
3. Prepare the run:
   ```sh
   .claude/scripts/prepare-run.sh
   ```
   It rebuilds and verifies the digests, prints the digest paths, and prints the base content JSON inventory `preparation` chooses from. Use this wrapper, never `profile_digest.py` or `ls`. `offer_*` and `patch_*` are previous applications' artifacts and are never a base.
4. Run `preparation` with Main paths, the base-JSON inventory and the job offer. Capture match summary, role framing, company slug, language and base content JSON path. Then resolve paths with `--print-paths`.
5. Run `generate-documents` with Main + CV + cover-letter paths, the preparation summary, the base content JSON path and the `cv_patch` and `cl_content` output paths. For a single document, inject only that output path and name it.
6. Render and verify yourself:
   ```sh
   career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en>
   ```
   It merges the patch, assembles the letter, selects the template, fits the page, applies dash hygiene, names the files, converts and verifies, and exits non-zero on failure. Use `--patch`/`--letter` for a non-canonical delta, or `--content`/`--cover-letter` to render a finished artifact. Run only this command — no `pdfinfo`, `pdftotext`, `grep`, `chromium`, `soffice` or `build_fit.py` checks of your own. Relay its verification report verbatim.
   If it fails because the letter exceeds one page at the scale cap, send it back to `generate-documents` once with the failing output and ask for a shorter draft. Never edit the letter yourself.
7. Present the match summary and the generated files (PDFs plus editable sources).
8. Report special wishes of the company (e.g. application by e-mail only) — only what the offer explicitly states. Never report the absence of one and never treat a missing one as blocking (`career-kb/communication-rules.md`, *Never frame by negation*).
