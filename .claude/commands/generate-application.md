---
description: Generate a tailored, ATS-optimized CV and/or cover letter from a job offer by orchestrating the preparation, generate-cv, generate-cover-letter, and output-generator subagents.
model: opus
---
# /generate-application — application pipeline (orchestrator)
You are the **orchestrator**. Never parse, write, or render yourself—delegate every phase via the Task tool and **inject** the required context into each prompt. Only this command references context files and subagents.
## Contexts
Read these files and inject their **contents** (never paths).
- **Main (every phase):** `career-kb/profile.json` (facts), `career-kb/general-standards.md` (branding), `career-kb/communication-rules.md` (voice)
- **Application (preparation, generate-cv, generate-cover-letter):** `career-kb/application-standards.md`
- **CV (generate-cv):** `career-kb/cv-standards.md`
- **Cover letter (generate-cover-letter):** `career-kb/cover-letter-standards.md`
- **Rendering (output-generator):**
  ```sh
  career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en>
  ```
  It selects canonical input paths automatically; use `--content`/`--cover-letter` only to override. It exits non-zero on failure.
## File naming
`render_application.py` is the single source of truth. Resolve all output paths by running:
```sh
career-kb/.venv/bin/python career-kb/tools/render_application.py --company <slug> --lang <de|en> --print-paths
```
Run this in step 3 and pass the resulting absolute paths to the generation subagents. Never hardcode filenames.
## Subagents
`preparation` → `generate-cv` / `generate-cover-letter` (parallel) → `output-generator`
## Asking
Ask only when guessing would be unsafe or waste work.
- Never ask for language/register—they come from `preparation`.
- Never ask for company slug, filenames, or paths—resolve them with `--print-paths`.
## Steps
1. Ask the user for the job offer.
2. Ask whether to generate **both**, **CV only**, or **cover letter only**.
3. Run `preparation`, injecting **Main + Application context + job offer**. Capture the match summary, role framing, company slug, then run `--print-paths`.
4. Run the selected generators **in parallel** if both were chosen:
   - `generate-cv`: inject **Main + Application + CV context + preparation summary + `cv_content` output path**.
   - `generate-cover-letter`: inject **Main + Application + Cover-letter context + preparation summary + `cl_source` output path**.
5. Run `output-generator`, injecting the **Rendering context**, company slug, and language(s). It renders and verifies the outputs.
6. Present the match summary and generated files (PDFs + editable sources).
7. Inform me if the company has any special whishes (e.g. application only per e-mail)