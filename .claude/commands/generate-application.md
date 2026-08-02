---
description: Generate a tailored, ATS-optimized CV and/or cover letter from a job offer by orchestrating the preparation and generate-documents subagents.
model: sonnet
---
# /generate-application — application pipeline (orchestrator)
You are the **orchestrator**. Never parse or write CV/cover-letter content yourself—delegate those phases via the Task tool. Only this command references context files and subagents.

You run on Sonnet on purpose. Orchestration here is path plumbing, two shell calls and relaying a verification report: no judgement about her career happens in this context. The judgement lives in `preparation`, which runs on Opus.

## Context injection: paths, never contents
Inject the **absolute paths** below into each phase and let the subagent read them. Do **not** read these files into your own context and do **not** paste their contents into a prompt: the fact base is ~19k tokens per phase, so copying it into a prompt would cost that in output tokens—the slowest and most expensive token class—to move data a subagent can read for a fraction of that.

The fact base is injected as a **phase-scoped digest**, never as `profile.json`. Digests are minified and pruned to what the phase provably reads (~42–45% cheaper than reading `profile.json`), and they are a gitignored build artifact, so **step 3 rebuilds them before use**.

- **Main (every phase):**
  - `career-kb/.digest/profile_<phase>.json` — facts (`<phase>` = `preparation` | `documents`)
  - `career-kb/general-standards.md` — branding
  - `career-kb/communication-rules.md` — voice
  - `career-kb/sound-like-human-standards.md` — required alongside `communication-rules.md` for every generated text
  - `career-kb/application-standards.md`
- **generate-documents also gets:**
  - `career-kb/cv-standards.md`
  - `career-kb/cover-letter-standards.md`
  - `career-kb/examples/coverletter_<slug>_<lang>.json` — the letter's tone/length reference. It lives in `examples/`, not `output/`, because `output/` holds disposable build artifacts and this file is a pipeline **input**. It names a real company, so it is kept locally and is NOT in git; on a fresh clone there is no tone reference and the cover-letter standards are the only guide. Inject the **`.json`**, not the `.html`: it is the same letter in the exact shape the phase must emit, so it doubles as the schema example and carries no CSS.

Pass every path a phase needs. A subagent that has to discover a path will explore the filesystem, which is forbidden and expensive—and the generation phase has no `Bash` tool, so it *cannot* look one up.

## File naming
`render_application.py` is the single source of truth. Resolve all output paths by running:
```sh
career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en> --print-paths
```
Run this after `preparation` (the slug does not exist until the offer has been read) and pass the resulting absolute paths to `generate-documents`. Never hardcode filenames.

## The generator emits deltas, the renderer emits documents
`generate-documents` writes no finished document. It writes two small files:
- **`cv_patch`** (`content/patch_<slug>_<lang>.json`) — only the changed CV fields. The renderer merges it onto the base and writes `cv_content` itself.
- **`cl_content`** (`output/coverletter_<slug>_<lang>.json`) — tagline, subject, salutation, paragraphs. The renderer pours it into `templates/coverletter_template_<lang>.html`, computes the date, and writes `cl_source`.

Inject those two paths, not `cv_content` / `cl_source`. Boilerplate the model retyped every run measured ~2,875 wasted output tokens per application, and output is both the priciest token class and the entire serial wall-clock. It is also a correctness win: a patch cannot corrupt a date or a company name it never mentions.

## Subagents
`preparation` (Opus) → `generate-documents` (Sonnet). **Rendering is not a subagent**—you run it yourself in step 5. The whole render takes ~1.7s of deterministic Python; wrapping it in an agent costs a spawn, ~8 turns and up to 40 minutes for no decision.

The CV and the letter are **one** agent, not two. They need the same digest, the same standards and the same match summary, so splitting them loaded ~19k tokens of identical context twice for no extra judgement.

## Asking
Ask only when guessing would be unsafe or waste work.
- Never ask for language/register—they come from `preparation`.
- Never ask for company slug, filenames, or paths—resolve them with `--print-paths`.

## Steps
1. Ask the user for the job offer.
2. Ask whether to generate **both**, **CV only**, or **cover letter only**.
3. Prepare the run with a single call:
   ```sh
   .claude/scripts/prepare-run.sh
   ```
   It rebuilds and verifies the digests, prints the digest paths, and prints the base content JSON inventory `preparation` chooses from. Use this wrapper, not `profile_digest.py` or `ls` directly: it validates that `profile.json` parses, checks that no digest lost a key or sub-key it should keep, confirms the GitHub honesty contract survived into every phase, deletes digests for phases that no longer exist, and lists only the role bases—`offer_*` and `patch_*` are previous applications' build artifacts, and picking one as a base would tailor a new application on top of another company's edits. Injecting a stale digest ships outdated facts silently, so this is not optional.
4. Run `preparation`, injecting **Main paths + the base-JSON inventory + the job offer**. Capture the match summary, role framing, company slug, language, and base content JSON path. Then resolve paths with `--print-paths`.
5. Run `generate-documents`, injecting **Main + CV + Cover-letter paths + the preparation summary + the base content JSON path + the `cv_patch` and `cl_content` output paths**. If the user asked for only one document, inject only that output path and say which one to write.
6. Render and verify yourself with a single command:
   ```sh
   career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en>
   ```
   It selects canonical input paths automatically—merging the CV patch and assembling the letter before it renders anything, so a malformed delta fails before Chromium starts. Use `--patch`/`--letter` to point at a non-canonical delta, or `--content`/`--cover-letter` to skip assembly and render a finished artifact. It handles template selection, page fitting, dash hygiene, file naming, sequential conversion, and verification, and exits non-zero on failure. Run **only** this command—no `pdfinfo`, `pdftotext`, `grep`, `chromium`, `soffice` or `build_fit.py` checks of your own. Relay its verification report verbatim.
   If it exits non-zero because the cover letter is still over one page at the scale cap, send it back to `generate-documents` **once** with the failing output and ask for a shorter draft. Never edit the letter down yourself.
7. Present the match summary and generated files (PDFs + editable sources).
8. Inform me if the company has any special whishes (e.g. application only per e-mail)
   **Only what the offer explicitly states.** Never report the *absence* of one, and never treat a missing one as an open question or as blocking submission. A posting with no application e-mail address, no destination URL, no contact person, no reference number and no requested document list is the normal case, not a finding — I know where I am applying. Report the channel only when the offer names it, and stay silent otherwise. (Same principle as `career-kb/communication-rules.md`, *Never frame by negation*: do not state what does not exist.)
