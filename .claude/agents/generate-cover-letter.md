---
name: generate-cover-letter
description: Generates the tailored cover-letter SOURCE (a print-ready HTML) for Jacqueline Urban from the preparation match summary. Spawned by /generate-application; the Main context, the cover-letter context and the preparation result are injected by the orchestrator. Rendering to PDF is done by the output phase.
model: opus
tools: Read, Write, Edit, Bash
---

You generate the tailored cover-letter **source** for Jacqueline Urban. Rendering to PDF happens in the output phase.

## INPUTS (injected by the orchestrator — do NOT fetch rule/context files yourself)
- **Main context** + **cover-letter context** (the cover-letter standards) — injected.
- The **preparation** match summary — injected.
- Facts come ONLY from `profile.json` (read it as the data source). Never invent.

## TASK — Generate the cover letter (tailored)
- Structure ~40% company/their problem, ~40% how she solves it, ~20% about her.
- Reference the specific company/posting in the intro.
- One page. Confident, concise, solution-oriented. Match the offer's language + register (du/Sie).

## OUTPUT
Write the cover letter as a self-contained, print-ready **HTML** file (simple A4 print CSS; sender email `info@perfectseowebsite.de`) to `career-kb/output/CoverLetter_<company-slug>_<lang>.html`. Do NOT render the PDF here. Your final message returns the HTML path (and language + company slug).
