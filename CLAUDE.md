## Efficiency-first execution
- Choose the lowest-token approach (model, agents, workflow, read/generate amount).
- Deviate only when the cheaper option loses more than 25% quality.

## Model selection
Pick the cheapest model that meets the quality bar (price per 1M tokens):
- **Haiku 4.5** ($1 / $5) — mechanical work: presence checks, grep, bulk read/extract/triage, formatting. Not multi-file reasoning.
- **Opus 4.8** ($5 / $25) — default for reasoning: tracing across `career-kb/`, verification, code review, and anything reaching an employer (`career-kb/profile.json`, `career-kb/content/*.json`, rendered CV and cover letter).
- **Fable 5** ($10 / $50) — one hard or orchestrating agent only: long autonomous runs, difficult first-shot builds, sub-agent coordination. Never for bulk verification; it is 2× Opus, slower, and false-positives.

## Hallucination reduction
- Take facts about [applicant] from `career-kb/profile.json` and `career-kb/content/`, never from memory.
- If a fact is missing there, ask. Never guess.

## No exploring — ever (hard rule)
- Never explore the filesystem unless explicitly instructed. No `ls`, `find`, `glob`, browsing, reading unspecified files, inspecting previous outputs.
- If a required path is missing, stop and name it. Do not work around prompt bugs.
- Exploration inflates context on every later call and pulls unrelated content into the task.

## Verification belongs to the renderer, not the generator
- `career-kb/tools/render_application.py` handles page fit, dash hygiene, email replacement, filenames and failure checks.
- Do not duplicate those checks and do not iterate to fit a page.
- The `preparation` and `generate-documents` subagents write their JSON once and stop. Merging, HTML assembly and PDF rendering belong to the renderer.

## Coding rules — read only for permanent code
- Read `CODING_RULES.md` before creating or changing permanent code: `career-kb/tools/`, `tests/`, `.claude/scripts/`, `Makefile`.
- Skip it for throwaway code: scratchpad scripts, one-off snippets, files deleted after the run.

## Document a rule at the highest context that fits — never lower
- Every rule lives in exactly one file: the most general one in which it is still true.
- A rule true for every channel goes into `career-kb/general-standards.md` (branding) or `career-kb/communication-rules.md` (voice).
- A rule belongs in a channel file (`cv-standards.md`, `cover-letter-standards.md`, `linkedin-standards.md`, `social-media-standards.md`) only if it is false for the other channels.
- Channel files reference the general rule instead of restating it.
- When a new source document repeats a universal rule, add the source reference only.
