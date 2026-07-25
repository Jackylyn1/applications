---
description: Generate a tailored, ATS-optimized CV and/or cover letter for Jacqueline Urban from a job offer. Orchestrates the preparation, generate-cv, generate-cover-letter and output-generator subagents and injects the relevant context into each.
model: opus
---

# /generate-application — application pipeline (orchestrator)

You are the **orchestrator**. Do NOT do the parsing / writing / rendering yourself — dispatch each phase to its subagent (via the Task tool) and **inject** the relevant context into that subagent's prompt. This command is the ONLY place that references contexts and subagents; the subagents never read the context files themselves.

## Contexts (the ONLY place these are referenced — inject the RELEVANT ones per phase)
Read these files and pass their **content** into the subagent prompts as noted. Do not just pass paths.
- **Main context (inject into every phase):** `career-kb/profile.json` (the only source of facts), `career-kb/general-standards.md`, `career-kb/communication-rules.md`
- **CV context (inject into generate-cv only):** `career-kb/cv-standards.md`
- **Cover-letter context (inject into generate-cover-letter only):** `career-kb/cover-letter-standards.md`
- **Rendering context (inject into output-generator only):** `career-kb/README.md` (rendering method) plus these exact commands:
  - CV: `career-kb/.venv/bin/python career-kb/tools/build_fit.py --content <content.json> --template <TEMPLATE> --out career-kb/output/Urban_CV_<Company>_<lang>.docx` where `<TEMPLATE>` = `career-kb/templates/CV_Template_Rezi_DE_Dec2025.docx` for German and `career-kb/templates/CV_Template_Rezi_Dec2025.docx` for English (this writes the PDF next to the .docx).
  - Cover letter: `chromium --headless=new --no-sandbox --disable-gpu --print-to-pdf=career-kb/output/Urban_CoverLetter_<Company>_<lang>.pdf <coverletter.html>` — the output path MUST be inside the project (snap Chromium cannot write to /tmp). If `chromium` is absent/fails, fall back to `soffice --headless --convert-to pdf --outdir career-kb/output <coverletter.html>`. Run PDF conversions sequentially.

## Subagents (referenced only here)
`preparation` → `generate-cv` / `generate-cover-letter` (parallel) → `output-generator`.

## Steps
1. **Get the job offer.** Ask the user to paste the job offer (text, a URL, or a PDF path) if they have not already provided one.
2. **Ask two SEPARATE questions (this is NOT either/or — both may be "yes", both may run in one execution):**
   - Question 1: *"Shall I generate a CV for this offer?"* (yes/no)
   - Question 2: *"Shall I generate a cover letter for this offer?"* (yes/no)
   If both are "no", stop.
3. **Preparation (always run first).** Spawn the `preparation` subagent, injecting the **Main context** + the job offer. Capture its structured match summary + role framing.
4. **Generation — run the selected branches IN PARALLEL (single message, both Task calls together) if both were chosen:**
   - If CV was "yes": spawn `generate-cv`, injecting **Main context + CV context + the preparation summary**. It returns a CV content-JSON path.
   - If cover letter was "yes": spawn `generate-cover-letter`, injecting **Main context + cover-letter context + the preparation summary**. It returns a cover-letter HTML path.
5. **Output.** Spawn `output-generator`, injecting the **Rendering context** + the generated source path(s) + company slug + language(s). It renders the PDF(s) and returns the run output.
6. **Present** the match summary and the produced files (PDFs + editable sources) to the user.
