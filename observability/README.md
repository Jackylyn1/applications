# observability — Claude Code token-cost tracking with Langfuse

This project's AI work runs through **Claude Code** (the CLI that orchestrates the
`career-kb` and `job-watch` skills and their subagents), not through direct
Anthropic API calls in our own code. So there is nothing in the codebase for the
Langfuse SDK to wrap at request time — but the token costs are still fully
recoverable: Claude Code writes every session as a JSONL transcript, and every
assistant turn carries a `usage` block (fresh input, cache-read, cache-creation,
output).

`cc_langfuse.py` reads those transcripts, prices each turn with the correct
per-model and cache-tier rates, and exports the result to Langfuse so cost is
**attributable by prompt, by cache read vs write, by growing context, by model,
and by session** — the exact breakdown needed to see where the tokens go and cut
them down.

## What it produces

- One **Langfuse session** per Claude Code session.
- One **trace** per user-prompt turn (named with the prompt text), carrying the
  turn's total cost and token/cost breakdown in metadata.
- One **generation** per API response (`message.id`), with `model`, token usage,
  and a `cost_details` split of **input / cache_read / cache_write / output** —
  so Langfuse's dashboards, grouping, and filters answer "where does the cost
  come from" directly.

## Quick start

```bash
# 1. Local breakdown — no account, no install (stdlib only):
python observability/cc_langfuse.py --report --latest
python observability/cc_langfuse.py --report --all

# 2. Install the exporter and point it at Langfuse:
pip install -r observability/requirements.txt
cp observability/.env.example observability/.env   # then fill in your keys

# 3. Preview exactly what would be sent (still sends nothing):
python observability/cc_langfuse.py --dry-run --latest

# 4. Export:
python observability/cc_langfuse.py --latest          # most recent session
python observability/cc_langfuse.py --all             # every session
python observability/cc_langfuse.py --session <id>    # one session (prefix ok)
```

The exporter is **idempotent**: traces and generations use deterministic ids
derived from the session and `message.id`, so re-running updates in place rather
than duplicating.

## Example (`--report`)

```
GRAND TOTAL - where the cost comes from
  fresh input (prompts+context)    $0.0002  ( 0.0% of $)             32 tok
  cache read                       $1.8158  (29.8% of $)      3,631,652 tok
  cache write                      $3.5525  (58.4% of $)        355,252 tok
  output                           $0.7194  (11.8% of $)         28,777 tok
  TOTAL $6.0879
  cache hit rate (read / prompt-side tokens): 100.0%
```

Reading this: cache **writes** dominate — a large stable prefix is being written
to cache repeatedly. The lever is prompt-cache placement / TTL, not output
length. That is the kind of conclusion this tool exists to make obvious.

## Fast local cost store — `cc_costs.py`

For reading costs back mechanically (no AI, no network), `cc_costs.py` ingests
transcripts once into an **indexed SQLite database** (`costs.db`) and reads them
out as fixed box tables. Pricing is computed at ingest time and stored, so reads
are pure SQL.

```bash
# Ingest transcripts (idempotent, incremental — safe to re-run any time,
# including while a task is still generating):
python observability/cc_costs.py ingest --all
python observability/cc_costs.py ingest --session <id>
```

Read it back with `.claude/scripts/cost-report.sh`, which ingests first and then
prints one table — task, model, calls, time, the cache split, tokens, cost:

```bash
.claude/scripts/cost-report.sh                                # newest session, per step
.claude/scripts/cost-report.sh --command generate-application # its LAST run, per step
.claude/scripts/cost-report.sh --command generate-application --by turn
.claude/scripts/cost-report.sh --command generate-application --runs --by command
.claude/scripts/cost-report.sh --session <id>                 # one terminal
.claude/scripts/cost-report.sh --agent <id> --by call         # inside one subagent
.claude/scripts/cost-report.sh --all --by command             # cost per command, ever
.claude/scripts/cost-report.sh --all --by model               # cost per model
.claude/scripts/cost-report.sh --today --by turn              # today, prompt by prompt
```

`--by step|turn|run|command|agent|model|session|call` picks the row
granularity; `--sort`, `--limit`, `--exact`, `--json` and `--no-ingest` do the
obvious. One application usually costs more than one run — `--like <text>`
keeps every run that mentions it, across terminals:

```bash
.claude/scripts/cost-report.sh --command generate-application --runs --like Company B --by run
``` The default (`--by step`) is the pipeline view — for one
`/generate-application` run: the main-thread orchestrator plus `preparation` →
`generate-cv` / `generate-cover-letter` → `output-generator`.

Three things worth knowing about the numbers:

- **A "run" is wider than a turn.** A slash command's work rarely fits in the
  turn that invoked it: the human answers a question, and each finished
  background agent comes back as its own turn. So a run spans from the command
  turn to the last turn it *caused* — a turn joins when it reports a result
  from an agent the run spawned (a `<tool-use-id>` back-reference, always
  causal) or spawns an agent itself within 30 min of the run's last activity.
  A later unrelated question is never billed to the command.
- **Subagents are attributed exactly**, not guessed: each one's sibling
  `.meta.json` carries the `Agent` call's `toolUseId`, which names the turn
  that spawned it.
- **Time is derived, not billed.** Transcripts carry no latency field, so a
  call's time is the gap ending at its response. The `time` column is model
  generation time only — it excludes tool execution and human think time,
  which is why it sits below the wall span printed under the table.

The DB is keyed on `message.id` (one billed API response), so re-ingesting never
duplicates. `costs.db` is git-ignored (regenerable from transcripts). Adding a
column? Re-run `ingest --all` to backfill it — the report says so when it finds
rows that predate turn tracking.

### Do we need this if we have Langfuse?

They're complementary, fed by the **same** parser + pricing core (`cc_langfuse`):

- **Langfuse** is the automatic dashboard layer. Once `cc_langfuse.py` exports,
  Langfuse stores every call's `cost_details` (the same four categories) indexed,
  and its UI rolls cost up by trace / session / model with filtering and trends —
  no SQL to write. Use it for exploring and watching cost over time.
- **`cc_costs.py` / `costs.db`** is the fast **local, offline, no-account** path:
  a millisecond SQL read that prints the exact CLI table for a task and its
  substeps. No network, no keys.

Neither can hook Claude Code's API calls *live* — both are fed by ingesting the
JSONL transcripts Claude Code writes. "During generation" = re-run `ingest`
(it's incremental); there is no real-time interception available for Claude Code.

## Pricing

`pricing.json` holds per-model input/output rates (USD per 1M tokens). Cache
costs are derived via Anthropic's universal multipliers (read 0.1×, write-5m
1.25×, write-1h 2×), so to update a model you only maintain its input/output
rate. Rates seeded from the Anthropic first-party price list — **verify against
<https://platform.claude.com/docs/en/pricing>**. Any model id not on the public
list (or flagged `_estimate`) is priced as a guess and called out in the report;
correct those before trusting the dollar figures.

## Notes / limits

- Transcript dir defaults to
  `~/.claude/projects/-home-jacqueline-Desktop-applications` — override with
  `--project-dir`.
- Subagents write their own transcripts under `<session>/subagents/`, so cost is
  attributed per named subagent, per turn, per command run and per model — see
  the run definition above for how a command's turns are grouped.
- Cost is derived from recorded token counts, not billed invoices — treat it as
  a high-fidelity estimate for optimization, not accounting.
