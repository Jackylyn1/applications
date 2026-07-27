# applications

Jacqueline Urban's job-application workspace — a set of Claude Code–driven tools
for finding roles and producing tailored, ATS-optimized applications.

## Components

| Directory | What it is |
|-----------|------------|
| [`career-kb/`](career-kb/README.md) | The career knowledge base: `profile.json` (single source of truth for all facts) plus channel-scoped standards, and the tooling that renders tailored CVs and cover letters (EN/DE) as PDFs. Drives the `/generate-application` and `/optimize-linkedin` skills. |
| [`job-watch/`](job-watch/) | Polls LinkedIn / Indeed / StepStone & co. for new offers, keeps each posting's text verbatim in `inbox/`, and notifies once per offer (`watch.py`). |
| `.claude/` | Skills (`commands/`) and subagents (`agents/`) that orchestrate the above. |

## Generating an application

Paste a job offer to Claude Code and run `/generate-application`. It loads
`profile.json` + the relevant standards, matches the posting's keywords against
real skills, flags honest gaps, and renders a tailored CV + cover letter (PDF)
in the offer's language and register. See
[`career-kb/README.md`](career-kb/README.md) for the full pipeline and the CV
build tooling.

**Principle:** applications are built only from facts in `profile.json` — she
never lies.
