---
description: Generate a tailored, ATS-optimized CV and/or cover letter from a job offer by orchestrating the preparation and generate-documents subagents.
model: sonnet
---
# /generate-application — application pipeline (orchestrator)
You orchestrate. Never parse or write CV/cover-letter content yourself; delegate via the Task tool. Only this command references context files and subagents.

Sonnet is correct here: orchestration is path plumbing, two shell calls and relaying a report. The career judgement lives in `preparation` (Opus).

## Context injection: paths, never contents
Inject the absolute paths below and let the subagent read them. Never read these files yourself and never paste their contents into a prompt. The fact base is ~19k tokens per phase.

Inject the fact base as a phase-scoped digest, never as `profile.json`. Digests are minified, pruned to what the phase reads (~42–45% cheaper) and gitignored, so step 3 rebuilds them first.

- **Main (every phase):**
  - `career-kb/.digest/profile_<phase>.json` — facts (`<phase>` = `preparation` | `documents`)
  - `career-kb/general-standards.md` — branding
  - `career-kb/communication-rules.md` — voice
  - `career-kb/sound-like-human-standards.md` — required alongside `communication-rules.md` for every generated text
  - `career-kb/application-standards.md`
- **generate-documents also gets:**
  - `career-kb/cv-standards.md`
  - `career-kb/cover-letter-standards.md`
  - `career-kb/examples/coverletter_<slug>_<lang>.json` — the letter's tone/length reference. Inject the `.json`, not the `.html`: it is the same letter in the shape the phase must emit. It names a real company and is not in git; on a fresh clone the cover-letter standards are the only guide.

Pass every path a phase needs. A subagent missing a path explores the filesystem, which is forbidden — and the generation phase has no `Bash` tool.

## File naming
`render_application.py` is the single source of truth. Resolve output paths with:
```sh
career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en> --print-paths
```
Run it after `preparation`, since the slug depends on the offer. Pass the resulting absolute paths to `generate-documents`. Never hardcode filenames.

## The generator emits deltas, the renderer emits documents
`generate-documents` writes two small files, never a finished document:
- **`cv_patch`** (`content/patch_<slug>_<lang>.json`) — changed CV fields only. The renderer merges it onto the base and writes `cv_content`.
- **`cl_content`** (`output/coverletter_<slug>_<lang>.json`) — tagline, subject, salutation, paragraphs. The renderer pours it into `templates/coverletter_template_<lang>.html`, computes the date and writes `cl_source`.

Inject those two paths, not `cv_content` / `cl_source`. Retyped boilerplate measured ~2,875 wasted output tokens per application, and a patch cannot corrupt a date or company name it never mentions.

## Subagents
`preparation` (Opus) → `generate-documents` (Sonnet). Rendering is not a subagent; you run it in step 6. It is ~1.7s of deterministic Python.

The CV and the letter are one agent. They need the same digest, standards and match summary, so splitting them loaded ~19k tokens twice for no extra judgement.

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
   It rebuilds and verifies the digests, prints the digest paths, and prints the base content JSON inventory `preparation` chooses from. Use this wrapper, not `profile_digest.py` or `ls`: it validates that `profile.json` parses, checks that no digest lost a key, confirms the GitHub honesty contract survived into every phase, deletes digests for dead phases, and lists role bases only. `offer_*` and `patch_*` are previous applications' build artifacts; picking one as a base tailors on top of another company's edits. A stale digest ships outdated facts silently.
4. Run `preparation` with Main paths, the base-JSON inventory and the job offer. Capture match summary, role framing, company slug, language and base content JSON path. Then resolve paths with `--print-paths`.
5. Run `generate-documents` with Main + CV + cover-letter paths, the preparation summary, the base content JSON path and the `cv_patch` and `cl_content` output paths. For a single document, inject only that output path and name it.
6. Render and verify yourself:
   ```sh
   career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en>
   ```
   It selects canonical input paths, merges the CV patch and assembles the letter before rendering, so a malformed delta fails before Chromium starts. Use `--patch`/`--letter` for a non-canonical delta, or `--content`/`--cover-letter` to render a finished artifact. It handles template selection, page fitting, dash hygiene, file naming, sequential conversion and verification, and exits non-zero on failure. Run only this command — no `pdfinfo`, `pdftotext`, `grep`, `chromium`, `soffice` or `build_fit.py` checks of your own. Relay its verification report verbatim.
   If it fails because the letter exceeds one page at the scale cap, send it back to `generate-documents` once with the failing output and ask for a shorter draft. Never edit the letter yourself.
7. Present the match summary and the generated files (PDFs plus editable sources).
8. Report special wishes of the company (e.g. application by e-mail only) — only what the offer explicitly states. Never report the absence of one, and never treat a missing one as an open question or as blocking submission. A posting without application address, destination URL, contact person, reference number or document list is the normal case. Stay silent otherwise (`career-kb/communication-rules.md`, *Never frame by negation*).
