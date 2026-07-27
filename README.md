# applications

Jacqueline Urban's job-application workspace — a set of Claude Code–driven tools
for finding roles and producing tailored, ATS-optimized applications.

## Components

| Directory | What it is |
|-----------|------------|
| [`career-kb/`](career-kb/README.md) | The career knowledge base: `profile.json` (single source of truth for all facts) plus channel-scoped standards, and the tooling that renders tailored CVs and cover letters (EN/DE) as PDFs. Drives the `/generate-application` and `/optimize-linkedin` skills. |
| [`job-watch/`](job-watch/) | Polls LinkedIn / Indeed / StepStone & co. for new offers, keeps each posting's text verbatim in `inbox/`, and notifies once per offer (`watch.py`). |
| `.claude/` | Skills (`commands/`) and subagents (`agents/`) that orchestrate the above. |

Session tracing runs on a self-hosted Langfuse outside this repo — see
[Observability](#observability--session-tracing).

## Generating an application

Paste a job offer to Claude Code and run `/generate-application`. It loads
`profile.json` + the relevant standards, matches the posting's keywords against
real skills, flags honest gaps, and renders a tailored CV + cover letter (PDF)
in the offer's language and register. See
[`career-kb/README.md`](career-kb/README.md) for the full pipeline and the CV
build tooling.

**Principle:** applications are built only from facts in `profile.json` — she
never lies.

## Observability — session tracing

Claude Code sessions are traced to a **self-hosted Langfuse** — turns,
generations, tool calls and token usage — through Langfuse's official Claude Code
plugin. It works through the `Stop` and `SessionEnd` hooks, so it adds no model
context.

**UI: <http://localhost:33000>** (port 3000 is taken by another container on this
machine).

Langfuse is machine-level infrastructure, **not part of this project**: it traces
every Claude Code session regardless of directory, and nothing in its
configuration references this repository. It therefore lives outside the repo and
is deliberately not versioned here.

| Where | What |
|---|---|
| `[path to langfuse]/` | the upstream clone — `docker compose up -d` · `down` · `ps` · `logs -f langfuse-web` |
| `[path to langfuse]/.env` | ports, secrets, login (mode `0600`) — the only place these values exist |
| `[path to langfuse]/docker-compose.override.yml` | the port bindings; upstream `docker-compose.yml` is untouched so `git pull` upgrades cleanly |
| `~/.claude/settings.json` | plugin config: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL` (the secret key lives in the OS keychain) |
| `~/.claude/state/langfuse_hook.log` | hook log — first place to look when traces don't arrive |

Health check: `curl -s -o /dev/null -w '%{http_code}\n' http://localhost:33000/api/public/health` → `200`.

### Activating it in Claude Code

Already active on this machine (`claude plugin list` shows it enabled). To set it
up elsewhere, take the project's API keys from the Langfuse UI
(Settings → API Keys) and:

```bash
claude plugin marketplace add langfuse/Claude-Observability-Plugin
claude plugin install langfuse-observability@langfuse-observability \
  --config LANGFUSE_PUBLIC_KEY=pk-lf-… \
  --config LANGFUSE_SECRET_KEY=sk-lf-… \
  --config LANGFUSE_BASE_URL=http://localhost:33000
```

`--config` is only read on install — a second `install` call on an already
installed plugin is a no-op, so change values later with `/plugin configure
langfuse-observability@langfuse-observability`. Hooks take effect in the **next**
session. Requires `uv` on PATH (or Python 3.10+ with `langfuse>=4.0,<5`).

Setup pitfalls that cost time once are recorded in
[`learnings.md`](learnings.md), not repeated here.
