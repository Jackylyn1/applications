# applications

Jacqueline Urban's job-application workspace — a set of Claude Code–driven tools
for finding roles and producing tailored, ATS-optimized applications.

## Components

| Directory | What it is |
|-----------|------------|
| [`career-kb/`](career-kb/README.md) | The career knowledge base: `profile.json` (single source of truth for all facts) plus channel-scoped standards, and the tooling that renders tailored CVs and cover letters (EN/DE) as PDFs. Drives the `/generate-application` and `/optimize-linkedin` skills. |
| [`job-watch/`](job-watch/) | Polls LinkedIn / Indeed / StepStone & co. for new offers, keeps each posting's text verbatim in `inbox/`, and notifies once per offer (`watch.py`). |
| [`observability/`](observability/README.md) | **Langfuse-based token-cost tracking for Claude Code.** Attributes cost by prompt, cache read/write, context, model, and session. |
| `.claude/` | Skills (`commands/`) and subagents (`agents/`) that orchestrate the above. |

## Observability — where do the token costs come from?

The AI work here runs through Claude Code, so cost is tracked by reading the
session transcripts rather than by wrapping API calls. **[Langfuse](https://langfuse.com)**
is the observability backend: `observability/cc_langfuse.py` prices each Claude
Code turn and exports it as Langfuse traces/generations, giving a per-prompt,
per-cache-tier, per-model, per-session cost breakdown. It also has a
zero-dependency local `--report` mode.

```bash
# Local breakdown, no account or install needed:
python observability/cc_langfuse.py --report --all

# Export to Langfuse (after: pip install -r observability/requirements.txt
#                      and cp observability/.env.example observability/.env):
python observability/cc_langfuse.py --all
```

See [`observability/README.md`](observability/README.md) for setup, pricing
configuration, and the mapping into Langfuse.

## Generating an application

Paste a job offer to Claude Code and run `/generate-application`. It loads
`profile.json` + the relevant standards, matches the posting's keywords against
real skills, flags honest gaps, and renders a tailored CV + cover letter (PDF)
in the offer's language and register. See
[`career-kb/README.md`](career-kb/README.md) for the full pipeline and the CV
build tooling.

**Principle:** applications are built only from facts in `profile.json` — she
never lies.
