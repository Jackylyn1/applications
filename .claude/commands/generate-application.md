---
description: Generate a tailored, ATS-optimized CV and/or cover letter from a job offer by orchestrating the preparation, generate-cv, and generate-cover-letter subagents.
model: opus
---
# /generate-application — application pipeline (orchestrator)
You are the **orchestrator**. Never parse or write CV/cover-letter content yourself—delegate those phases via the Task tool. Only this command references context files and subagents.

## Context injection: paths, never contents
Inject the **absolute paths** below into each phase and let the subagent read them. Do **not** read these files into your own context and do **not** paste their contents into a prompt: the fact base is ~32k tokens, so copying it into three prompts would cost ~100k output tokens—the slowest and most expensive token class—to move data a subagent can read for a fraction of that.

The fact base is injected as a **phase-scoped digest**, never as `profile.json`. The digests are minified and per-phase pre-scoped (~39% cheaper to read), and they are a gitignored build artifact, so **step 3 rebuilds them before use**.

- **Main (every phase):**
  - `career-kb/.digest/profile_<phase>.json` — facts (`<phase>` = `preparation` | `cv` | `cover-letter`)
  - `career-kb/general-standards.md` — branding
  - `career-kb/communication-rules.md` — voice
  - `career-kb/sound-like-human-standards.md` — required alongside `communication-rules.md` for every generated text
- **Application (preparation, generate-cv, generate-cover-letter):** `career-kb/application-standards.md`
- **CV (generate-cv):** `career-kb/cv-standards.md`
- **Cover letter (generate-cover-letter):** `career-kb/cover-letter-standards.md`, plus `career-kb/examples/coverletter_dmc_de.html` as the structure/tone reference (it lives in `examples/`, not `output/`, because `output/` is gitignored and this file is a pipeline **input**)

Pass every path a phase needs. A subagent that has to discover a path will explore the filesystem, which is forbidden and expensive—and the generation phases have no `Bash` tool, so they *cannot* look one up.

`preparation` picks the base content JSON, so it must be told which ones exist. Inject the inventory:
```sh
ls -1 career-kb/content/
```
Without it, `preparation` would have to guess a filename from the role name and could name a file that does not exist.

## File naming
`render_application.py` is the single source of truth. Resolve all output paths by running:
```sh
career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en> --print-paths
```
Run this in step 3 and pass the resulting absolute paths to the generation subagents. Never hardcode filenames.

## Subagents
`preparation` → `generate-cv` / `generate-cover-letter` (parallel). **Rendering is not a subagent**—you run it yourself in step 5. The whole render takes ~1.7s of deterministic Python; wrapping it in an agent costs a spawn, ~8 turns and up to 40 minutes for no decision.

## Asking
Ask only when guessing would be unsafe or waste work.
- Never ask for language/register—they come from `preparation`.
- Never ask for company slug, filenames, or paths—resolve them with `--print-paths`.

## Steps
1. Ask the user for the job offer.
2. Ask whether to generate **both**, **CV only**, or **cover letter only**.
3. Rebuild the digests, then run `preparation`:
   ```sh
   .claude/scripts/rebuild-digests.sh
   ```
   Use this wrapper, not `profile_digest.py` directly: it also validates that `profile.json` parses and verifies that no digest lost a key it is supposed to keep. Injecting a stale digest ships outdated facts silently, so this is not optional. Then run `preparation`, injecting **Main + Application paths + the base-JSON inventory + the job offer**. Capture the match summary, role framing, company slug, and base content JSON path, then run `--print-paths`.
4. Run the selected generators **in parallel** if both were chosen:
   - `generate-cv`: inject **Main + Application + CV paths + preparation summary + the base content JSON path + the `cv_content` output path**.
   - `generate-cover-letter`: inject **Main + Application + Cover-letter paths + preparation summary + the `cl_source` output path**.
5. Render and verify yourself with a single command:
   ```sh
   career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en>
   ```
   It selects canonical input paths automatically; use `--content`/`--cover-letter` only to override. It handles template selection, page fitting, dash hygiene, file naming, sequential conversion, and verification, and exits non-zero on failure. Run **only** this command—no `pdfinfo`, `pdftotext`, `grep`, `chromium`, `soffice` or `build_fit.py` checks of your own. Relay its verification report verbatim.
   If it exits non-zero because the cover letter is still over one page at the scale cap, send the letter back to `generate-cover-letter` **once** with the failing output and ask for a shorter draft. Never edit the letter down yourself.
6. Present the match summary and generated files (PDFs + editable sources).
7. Inform me if the company has any special whishes (e.g. application only per e-mail)
