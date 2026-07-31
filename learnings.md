# Learnings

A running log of what we built, what broke, what the numbers actually were, and
why. Updated after every task.

Three audiences, in this order:
1. **Us** — so a fix is never rediscovered twice.
2. **Applications** — concrete, measurable engineering evidence for CVs and
   cover letters (see `career-kb/profile.json` for the fact base; anything moved
   there must survive the "never lie" rule).
3. **LinkedIn / posts** — raw material at the bottom of each entry.

**Honesty rule for this file:** numbers are measured, not estimated, unless
explicitly labelled. Where a figure is a guess, it says so.

---

## 2026-07-25 — `/generate-application` end-to-end test, then instrumenting it

### What happened

Ran the full four-phase pipeline (`preparation` → `generate-cv` ∥
`generate-cover-letter` → `output-generator`) against a synthetic German job ad
for a fictional "Company A GmbH" (Senior PHP-Entwickler:in mit KI-Fokus,
`du` register, two deliberate skill gaps planted to test honest gap-flagging).

It worked end to end and produced a correct 2-page CV and 1-page cover letter.
Then we measured it, found five design defects, fixed four, and instrumented the
whole thing.

### Defects found by testing (not by reading)

| # | Defect | Fix |
|---|--------|-----|
| 1 | Orchestrator said "inject file *content*", agent specs said "*read* `profile.json`" — contradictory | fixed by hand |
| 2 | Dash hygiene enforced only on the CV path; the cover letter shipped **12 en dashes** into the PDF | extracted `tools/ats_hygiene.py`, imported by both paths |
| 3 | `README.md` duplicated the render commands and had **drifted** — it documented a CV rendered from HTML, contradicting the hard rule that CVs come from the stored DOCX template | README reduced to an index; commands documented once |
| 4 | Two filename conventions in one run (`offer_Company A_de.json` vs `Urban_CV_Company A_de.pdf`) | naming defined once, in `tools/render_application.py`; agents call `--print-paths` |
| 5 | Cover letter invented an `Anlagen:` line nothing had specified | banned in `cover-letter-standards.md` |

The pattern in 2/3/4: **duplication drifts.** Every one of those defects was two
copies of one rule disagreeing. That is now a standing project rule.

### The timing investigation — and a correction

First conclusion was wrong, so it is recorded here as well as the right one.

**Claimed first:** the 41-minute output phase was agent overhead — a Haiku agent
burning 13 tool calls on a 9-item verification checklist.

**Actually measured:** of that phase's 40m42s, only **1m00s was model time** and
**21.8s was real tool execution**. **39m20s was two permission-approval prompts
waiting on a human.** The agent was not slow; it was blocked.

Measured render times (`/usr/bin/time`, not estimates):

| Command | Real runtime |
|---|---|
| `build_fit.py` (CV: fill template, page-length rule, PDF) | **0.51 s** |
| `chromium --headless` (cover letter → PDF) | **0.57 s** |
| `render_application.py` (both + 12 verification checks) | **1.16 s** |

So the output phase does ~1.1 s of work. Everything else was waiting.

### Where one pipeline run actually goes

Per-phase, derived from the Claude Code transcripts. Method validated: computed
spans match the harness-reported durations **exactly** (134 s / 678 s / 1628 s /
2442 s).

| Phase | Span | Model time | Real tool exec | Blocked on approval |
|---|---:|---:|---:|---:|
| 1 preparation | 2m14s | 2m14s | 0.4s | 0 |
| 2a generate-cv | 11m18s | 3m33s | 0.4s | 7m45s (1 prompt) |
| 2b generate-cover-letter | 27m08s | 4m24s | 1m08s | 21m36s (2 prompts) |
| 3 output-generator | 40m42s | 1m00s | 21.8s | 39m20s (2 prompts) |
| **Sum** | **1h21m** | **11m11s** | **1m30s** | **1h08m** |

- **Observed wall clock, critical path:** ~**70 minutes**
  (prep 2m14 → slowest parallel branch 27m08 → output 40m42).
- **Actual compute:** **11m11s of model time + 1m30s of tool execution.**
- **84% of the run was five permission prompts.**

**The headline number:** the output phase went from **40m42s → 1.16 s**. But the
honest mechanism is three things, not one: approval prompts 2 → 1, model time
1m00s → ~10s, and verification moved from an LLM checklist into deterministic
code. The single biggest lever was **removing human-approval round-trips**, not
making the model faster.

**Projected clean run** (no approval friction): prep 2m14 + slowest branch ~4m30
+ output ~5s ≈ **under 7 minutes**, down from 70.

### Cost

Session total **$13.31** — but see the caveat.

| Where the money goes | Share |
|---|---|
| cache read (13.05M tokens) | 49.3% |
| cache write | 33.6% |
| output (92k tokens) | 17.3% |
| fresh input | ~0% |

Cache hit rate on prompt-side tokens: **100%**. Cost is dominated by *re-reading
a large context*, not by generating text — the lever is context size and cache
placement, not output length.

**Caveat:** `claude-opus-5` is flagged `_estimate` in `pricing.json`, so the
dollar figures are unverified guesses at $5/$25 per Mtok. The *token* counts and
*all timing numbers* are exact. Verify rates before quoting the dollars anywhere.

### Observability: three real bugs in the exporter

`observability/cc_langfuse.py` reads Claude Code JSONL transcripts and ships
cost to Langfuse. Testing it against a real pipeline run found:

1. **All subagent data was invisible.** Subagent transcripts live in
   `<project>/<session>/subagents/agent-<id>.jsonl`, not in the project root the
   tool globbed. `isSidechain` is always `false` in the main transcript — the
   README's claim that subagent turns "fold into the main chain" is wrong. For
   this pipeline that meant missing **84% of wall clock** and most tokens.
2. **Every duration exported as zero.** Generations were emitted with
   `start_time == end_time`, so Langfuse would render the entire pipeline as
   instantaneous — useless for finding slow steps, which is the main reason to
   have traces at all.
3. **Haiku was priced at Opus rates.** Model ids carry decorations the price list
   lacks (`claude-haiku-4-5-20251001`, `claude-opus-5[1m]`). Exact-string
   matching dropped them onto `default` — a **5× cost overstatement** for Haiku.

Fixed all three, plus added a `--timing` report (wall clock split into model vs
tool vs idle, per subagent, naming the slowest calls). Export now produces
**16 traces / 132 generations with real latencies**, subagents included and
separately tagged.

**Still open:** Langfuse itself is not actually running. No SDK installed, no
`.env`, no server. `--report`, `--timing` and `--dry-run` work standalone
(stdlib only); shipping to a real Langfuse needs either cloud keys or a local
instance.

### Transferable engineering lessons

- **Measure before optimizing — then re-measure.** The first diagnosis
  ("chatty agent") was plausible and wrong. `/usr/bin/time` on the actual
  command settled it in seconds and pointed at a completely different cause.
- **A number without a mechanism is a story.** "41 min → 1.16 s" is true and
  useless until you can say *which* of the three changes did the work.
- **Validate a measurement method against ground truth.** Transcript-derived
  spans were only trustworthy because they matched harness-reported durations
  exactly.
- **Instrumentation needs testing like any other code.** A cost tracker that
  silently omits 84% of the workload and reports every duration as zero looks
  perfectly healthy until you check it against a run you already understand.
- **Duplication is a latent bug.** Three of five pipeline defects were two
  copies of one rule that had drifted apart.
- **Human round-trips dominate agent pipelines.** Model latency was 14% of wall
  clock; waiting for approvals was 84%. Optimizing tokens would have been the
  wrong project.

### Raw material for LinkedIn / posts

Honest angles, each backed by a measured number above:

- *"I thought my AI pipeline was slow. I measured it: 84% of the runtime was it
  waiting for me to click Approve."* — the approval-latency finding, with the
  11m11s vs 1h08m split.
- *"My cost tracker was reporting zero-duration traces and pricing Haiku at Opus
  rates."* — testing your own observability; the three-bug list.
- *"Two copies of one rule will drift. Mine documented a workflow the code no
  longer supported."* — the README-vs-template contradiction; single source of
  truth as a working practice.
- *"An LLM verifying its own output with 13 shell commands vs. 12 assertions in
  a script that runs in 1.16 seconds."* — determinism where determinism belongs;
  keep the model for judgment, not for checking.
- *"Cache reads were 49% of my bill at a 100% hit rate — the lever was context
  size, not output length."*

**For CV / cover letters** (only after verifying against `profile.json` rules):
this is genuine evidence of performance measurement, instrumentation, root-cause
analysis under a wrong first hypothesis, and turning an LLM step into
deterministic tooling. Frame it as AI-assisted work on her own tooling — she
directed the investigation and the design decisions; do not present it as
production work for an employer.

---

## 2026-07-25 (later) — run 2: removing the friction, and measuring it

### Why the pipeline kept asking

Two unrelated causes, easy to confuse:

1. **The command's own questions.** `generate-application.md` step 1 said "Ask
   the user to paste the job offer" and step 2 said "Ask two SEPARATE
   questions", *unconditionally* — even when the offer was already in the
   conversation and both documents were obviously wanted. It asked because it
   was told to.
2. **Harness permission prompts.** `.claude/settings.local.json` held ~90
   **exact-match** entries, accumulated one approval at a time — including the
   previous run's full command with the company slug baked into the path. Since
   every run produces new argument combinations, nothing matched and every call
   prompted again. An allowlist of literals cannot generalize.

Fixes: an "never ask for what you can already answer" section in the command
(offer taken from the conversation; **both** documents are the default;
language, register, slug and paths are always derived, never asked), and
**pattern-based** permission rules scoped to the pipeline's stable shapes
(`render_application.py *`, writes under `career-kb/content/**` and
`career-kb/output/**`). Also added `--page-check` so the cover-letter agent can
verify one-page-ness through the same script instead of inventing its own
`chromium` command in a temp directory.

### Run 1 vs run 2 — same offer, same phases, measured identically

| | Run 1 | Run 2 | |
|---|---:|---:|---|
| **Critical path (wall clock)** | **70m04s** | **5m19s** | **13.2× faster** |
| Sum of all four phase spans | 1h21m | 8m09s | 10.0× |
| Model time | 11m11s | 8m03s | 1.4× |
| Real tool execution | 1m30s | 5.6s | 16.3× |
| **Blocked on approval** | **1h08m** | **0s** | eliminated |
| Approval prompts | 5 | **0** | |
| API calls | 51 | 23 | −55% |
| Cache-read tokens | 1,574,523 | 686,763 | −56% |
| Cache-write tokens | 331,493 | 131,400 | −60% |
| Output tokens | 5,869 | 4,368 | −26% |
| Cost (estimated) | $2.71 | $1.23 | −55% |

Per phase (span): preparation 2m14s → 1m59s · generate-cv 11m18s → 3m07s ·
cover-letter 27m08s → 2m50s · **output 40m42s → 12.6s (194×)**.

**What actually produced the speedup**, in order of contribution:
1. **Zero approval prompts** — worth 1h08m on its own, ~84% of run 1.
2. **The output phase became one command** — 13 tool calls → 1, and the model
   stopped hand-writing verification shell commands.
3. **Tighter agent prompts** (explicit output paths, "no exploratory shell
   commands") — API calls 51 → 23, which is where the token halving comes from.

Model time barely moved (11m11s → 8m03s). **The generation was never the
bottleneck.** Everything that mattered was around it.

### Incident: the artifacts were deleted mid-measurement

After run 2 finished, `career-kb/output/` and `career-kb/content/` were emptied
of the run's outputs at 19:29, and a file nothing in this session wrote —
`career-kb/offer_Company A_de.md`, self-described as a *reconstructed*
job offer rebuilt from the phase-1 parse — appeared at 19:20. A **concurrent
Claude Code session** was operating in the same repo.

Recovery, and the lesson in it: the sources were rebuilt by replaying the
subagent transcripts. The first attempt replayed only `Write` calls and produced
a **2-page** cover letter — because the agent had written the letter and then
**trimmed it with 7 `Edit` calls** to make it fit. Replaying `Write` *and*
`Edit` in order restored it exactly (484 words, 1 page, 12/12 checks).

- **A transcript is a replayable log, but only if you replay every mutation.**
  Write-only recovery silently produces a plausible, wrong artifact.
- **Concurrent agent sessions in one repo will clobber each other.** Nothing
  here was version-controlled at the time; git would have made this a non-event.
- The measurement itself survived because it came from transcripts, not from
  the files. **Derive metrics from an append-only source, not from mutable
  output.**

### Raw material for LinkedIn / posts

- *"I made my AI pipeline 13× faster without touching the model. 84% of the
  runtime was permission prompts; the model was never the bottleneck."*
  70m04s → 5m19s, model time 11m11s → 8m03s.
- *"My allowlist had 90 entries and matched nothing — it stored literals, not
  patterns, so every run re-asked for permission it had already been given."*
- *"The output step went from 40 minutes to 12 seconds by deleting the agent
  from it."* 194×, and the honest breakdown of why.
- *"Halving the token bill was a side effect of telling agents exactly where to
  write."* 51 → 23 API calls, $2.71 → $1.23.
- *"Two AI sessions in one repo deleted each other's work. I rebuilt it from the
  transcripts — and learned that replaying only the writes gives you a
  convincing wrong answer; you have to replay the edits too."*

## 2026-07-25 (later still) — run 3: first real offer through the tuned pipeline

Same pipeline as run 2, but a genuine job offer instead of the recurring test
case: Company K, *Software Engineer – Developer Experience / Tooling (PHP)*.
First run where the interesting failure modes were about **content honesty**,
not plumbing.

### Numbers

| | Run 2 (test offer) | Run 3 (Company K) |
|---|---|---|
| Wall clock (start → PDFs) | 5m19s | ~9m |
| Approval prompts | 0 | 0 |
| Human round-trips | 1 (offer) | 2 (offer + scope) |
| Subagent tokens | — | 179,548 |
| Subagent tool calls | 48 total | 48 total |
| Render checks | 12/12 | 12/12 |

Per phase (span): preparation 3m35s · generate-cv 3m26s · cover-letter 4m54s
(the two ran in parallel, so they cost 4m54s of wall clock, not 8m20s) ·
output **26s**.

Per phase (tokens / tool calls): preparation 43,634 / 8 · generate-cv 66,098 / 12 ·
cover-letter 54,996 / **25** · output 14,820 / 3.

### Why this run was slower than run 2, and why that is fine

Run 2's 5m19s was on an offer the pipeline had already seen. Run 3 was longer for
reasons that are all *work*, not friction:

1. **Parallelism held.** CV and cover letter ran as one message, two Task calls.
   Wall clock for the generation phase = the slower branch (4m54s), not the sum.
   Without it the run would have been ~12m30s.
2. **The cover letter cost 25 tool calls to the CV's 12** — and 7 of those were
   trim edits to force one page. Same pattern as the run-2 recovery incident:
   *the letter is written long and then cut.* The page-length rule is enforced
   after the fact, by iteration, not by the prompt. That is the next thing worth
   fixing — a target word count in the brief would trade 7 edits for 0.
3. **The output phase stayed at 26 seconds**, three tool calls, 12/12 checks.
   The single-command output phase from run 2 is holding up on unseen input.

### The real work this run: honesty guards

The offer asked for Go ("a plus") and is a Company K role; the profile has neither.
This is exactly where a tailoring pipeline invents things. What stopped it was
that phase 1 emitted the guards **as binding table rows** and the orchestrator
injected them verbatim into both generators:

- **Go** — zero CV mentions (grep-verified), and one flat sentence in the letter:
  *"And I do not write Go."* Not "basics", not "currently learning". Mitigation
  is the offer's own words about learning new languages, backed by Python
  (~360 commits in ~2 months) and TypeScript.
- **Shopware** — one clause, cover letter only: set up a dockware environment for
  a trial task, *"and that is the extent of it."* Never on the CV.
- **The OSS package** — the profile flags it as a fork with **1 commit on top of
  187 upstream**. Both documents say "contributed a feature to an existing
  open-source Laravel package", never "built a package".
- **Scope of ownership** — "designed and own specific components end-to-end",
  never "architected the platform".
- **Test claims** — attached only to the employer where tests actually exist. Two
  public repos have phpunit config and no real tests; the CV **dropped one of
  them entirely** rather than cite it near a testing claim.

Both generators reported the guards back unprompted, with grep verification.
**A gap table with explicit forbidden phrasings survives two hops of prompt
injection; a vague "be honest" does not.**

### Transferable lessons

- **Parallelism is only worth it when the branches are genuinely independent.**
  CV and cover letter share one brief and write to different files — the ideal
  case. It halved the generation phase.
- **Enforcement-by-iteration is invisible in the output and expensive in the
  transcript.** The letter is one page in the PDF either way; only the tool-call
  count reveals it took 7 edits. Metrics from artifacts would have missed this.
- **Say what NOT to write.** The guards that worked were phrased as banned
  strings ("never 'built a package'"), not as principles.
- **A named contact changes the document.** The offer named a recruiter, so the
  letter is addressed to a person rather than to a company — free specificity
  the pipeline only gets if phase 1 is told to look for it.

### Raw material for LinkedIn / posts

- *"My AI application pipeline was asked for Go experience I do not have. It
  wrote: 'And I do not write Go.' That sentence is the whole product."* The gap
  table, and why forbidden phrasings beat 'be honest'.
- *"I ran CV and cover letter as two parallel agents. The generation phase cost
  4m54s instead of 8m20s — the slower branch, not the sum."*
- *"The cover letter took 25 tool calls; the CV took 12. Seven of the difference
  were edits trimming it to one page. The PDF looks identical either way —
  only the transcript shows the pipeline is enforcing length by iteration."*
- *"An honest CV is a subtraction problem. Mine dropped a whole project rather
  than let it sit next to a testing claim it could not support."*
- *"179,548 tokens, 48 tool calls, 12/12 checks, ~9 minutes, zero permission
  prompts, one tailored CV and cover letter."*

---

## Run: Company B GmbH — Senior Software Engineer (PHP/TS/Node), DE, 2026-07-25

### The numbers

| Phase | Model | Calls | Cache write | Cache read | Output | Total tokens | Cost (1h TTL) |
|---|---|---|---|---|---|---|---|
| Orchestrator | Opus 5 | 27 | 76,558 | 1,367,235 | 49,234 | 1,493,080 | $2.68 |
| preparation | Opus 5 | 16 | 105,584 | 456,903 | 11,772 | 574,291 | $1.58 |
| generate-cv | Opus 5 | 22 | 115,116 | 815,583 | 20,350 | 952,685 | $2.08 |
| generate-cover-letter | Opus 5 | 33 | 115,354 | 978,265 | 16,890 | 1,110,575 | $2.07 |
| output-generator | Haiku 4.5 | 8 | 19,118 | 52,786 | 1,606 | 73,578 | $0.05 |
| **Total** | | **106** | **431,730** | **3,670,772** | **99,852** | **4,204,209** | **~$8.45** |

Wall clock: prep 288s, CV 244s, cover letter 293s (parallel), render 36s.
12/12 render checks passed on the first attempt, zero re-runs.

> **CORRECTION (2026-07-26): every absolute number in this section is ~2x too
> high. Do not quote it.** It counted usage-bearing JSONL *lines* (102 in this
> window) instead of billed API *responses* (51). Claude Code streams one
> response across several lines that share a `message.id` **and a `requestId`**,
> repeating the same `cache_read` / `cache_creation` values each time; summing
> the lines double- and triple-counts them. The giveaway: the 431,730 "write
> tokens" above is the naive line sum (431,630), against 214,257 actually
> billed.
>
> Verified figures for this run (`cost-report.sh --command generate-application`,
> collapsed per `message.id`, cache tiers priced from the transcript's own
> 5m/1h split): **51 calls, 214,257 write, 1,783,371 read, 65,063 output,
> 2.06M tokens, $3.94**, 15m29s model time inside a 16m16s wall span. Per step:
> orchestrator $1.11 (28.2%), generate-cv $1.03, generate-cover-letter $1.03,
> preparation $0.75, output-generator on Haiku $0.02 (0.6%).
>
> The proportional conclusions below survive — cache reads still dominate token
> volume while costing a tenth of list, output is still ~a third of spend, Haiku
> rendering is still ~0.6% — but the dollar and token figures in them are not
> real. The TTL bullet is also moot: the tiers are recorded per call, so nothing
> has to be assumed.
>
> **The Company B application as a whole was not one run.** Three
> `/generate-application` runs touched it: 18:35 ($2.83, first attempt), 18:46
> ($0.40, abandoned immediately), 19:40 ($3.94, the complete one) —
> **$7.17 total**. A remembered "about 8 euros" is that sum, not this run.

### Cost structure

- **Cache reads are 87% of tokens and 21% of cost.** 3.67M read tokens at 0.1x
  input price = $1.84. The volume number is nearly meaningless as a cost proxy.
- **Output tokens are 1.2M-equivalent in spend.** 99,852 output tokens at $25/M
  = $2.50 — a quarter of the run, from 2.4% of the tokens.
- **Cache-write TTL is the single largest cost lever.** 431,730 write tokens at
  1h TTL (2x) cost $4.29; at 5m TTL (1.25x) they would cost $2.68. The whole run
  swings $6.9 -> $8.5 on that one multiplier.
- **Haiku on the render phase cost $0.05 — 0.6% of the run** for the phase that
  produced the actual deliverables. Model tiering paid for itself.

### What the split says

- The cover-letter agent used **50% more calls than the CV agent** (33 vs 22) for
  fewer output tokens — page-fit iteration again, same pattern as the prior run.
- The orchestrator is the **most expensive single line item** ($2.68). Its cost is
  context re-reads plus the two ~2,000-token injected agent prompts. Injecting
  full context into subagents is not free; it is roughly one subagent's worth.
- **Two human round-trips** (deliverable choice, then Java/Elasticsearch facts).
  The second one was worth it: "Grundlagen aus dem Studium" is a claim the
  pipeline could not have derived from profile.json and would have had to omit.

### Raw material for LinkedIn / posts

- *"One tailored CV + cover letter: 4.2M tokens, 106 model calls, $8.45, nine
  minutes. 87% of those tokens were cache reads costing a tenth of list price."*
- *"I run the rendering phase on Haiku. It is 0.6% of the run cost and produces
  100% of the files the recruiter actually opens."*
- *"The orchestrator was my most expensive agent — more than any worker. Passing
  full context down to subagents costs about one subagent."*
- *"My pipeline asked me two questions it could not answer from data: do you know
  any Java, and are you actually learning Elasticsearch. One answer became a
  sentence in the letter. The other deleted a line. Both were right to ask."*

## 2026-07-26 — rewriting the cost report: attribution is the hard part, not SQL

### What happened

`cost-report.sh` was a 170-line bash+Python heredoc that re-parsed every JSONL
transcript and re-derived pricing on each run — a second implementation of what
`observability/cc_costs.py` already did into an indexed SQLite store. It also
could not answer the one question worth asking: *what did the last
`/generate-application` cost?* Rewrote it as a 60-line wrapper: ingest, then one
table. All parsing, pricing and SQL stay in `cc_costs.py`; see its docstring.

New table: `task | model | calls | time | fresh in | cache rd | cache wr |
output | tokens | cost | %`, with `--by step|turn|run|command|agent|model|
session|call` and scopes `--command <name>` (last run), `--session`, `--agent`,
`--all`, `--today`.

### The wrong turn, and it was a 30x error

First implementation attributed each API call to its `promptId` and called that
"the run". Filtering the last `/generate-application` returned **1 call, $0.13**.
The real run was **51 calls, $3.94** — a **30x undercount** that looked
plausible enough to ship.

Cause: a slash command's work does not live in the turn that invoked it. The
command turn only spawns the skill (46 output tokens). The human then pastes the
offer in a *new* turn, and every finished background agent comes back as its own
turn — 6 turns, 4 subagent transcripts, one logical run.

Fix: assemble runs causally. A turn joins the open run if it back-references a
`<tool-use-id>` the run spawned (always causal) or spawns an `Agent` itself
within 30 min. Turns sandwiched between the command and the last caused turn
come along; anything after it does not. The follow-up question two minutes later
("what did that cost?", $4.19 on its own) is correctly excluded.

### Numbers

Last `/generate-application` run, measured by the new tool:

| Step | Model | Calls | Time | Tokens | Cost | Share |
|---|---|---|---|---|---|---|
| Orchestrator | Opus 5 | 12 | 2m57s | 631.6k | $1.11 | 28.2% |
| generate-cv | Opus 5 | 10 | 4m03s | 468.1k | $1.03 | 26.1% |
| generate-cover-letter | Opus 5 | 17 | 3m39s | 611.6k | $1.03 | 26.1% |
| preparation | Opus 5 | 8 | 4m35s | 314.7k | $0.75 | 19.1% |
| output-generator | Haiku 4.5 | 4 | 15.5s | 37.6k | $0.02 | 0.6% |
| **Total** | | **51** | **15m29s** | **2.06M** | **$3.94** | |

- Wall span 16m16s vs 15m29s summed model time — the four agents barely
  overlapped. Parallelism is on paper, not in the clock.
- Cache hit 89.2%; 70 output tok/s; $0.25 per minute of model time.
- Reading the DB: **34 ms**. With a full re-ingest of 57 transcripts: **450 ms**.
  1,081 calls / 12 sessions / 43 subagents / 4 command runs in a 696 KB file.
- Orchestrator is again the largest line item (28.2%), same as run 3. Haiku on
  rendering is again ~0.6%. Two runs, same shape.

### The second wrong number, found by being challenged

Asked "are you sure? we had something like 8 EUR before", and the answer was
that *both* numbers were wrong, in opposite directions:

- The old **$8.45** for this run was a **~2x overcount** — it summed
  usage-bearing JSONL lines instead of billed responses. Streaming emits 2-3
  lines per response sharing one `message.id` *and* `requestId`, each repeating
  the same cache-read/cache-write figures. 102 lines, 51 responses. Corrected in
  the Company B section above.
- But **$3.94 was not the Company B total either.** Three `/generate-application`
  runs went into that application — 18:35 $2.83, 18:46 $0.40 (abandoned), 19:40
  $3.94 — **$7.17**. Reporting "the last run" as "the Company B run" was the
  narrower error. Added `--like <text>` so a whole application can be pulled
  across runs and terminals: `--command generate-application --runs --like
  Company B` → $6.77 across the two runs that reached the offer.
- Also worth separating: that same session spent a further **$9.72 after the
  pipeline finished**, on the conversation analysing what it had cost. The
  session total is $13.66; the pipeline is $3.94. Measuring is not free, and
  here it cost 2.5x the thing being measured.

### Transferable lessons

- **Two numbers disagreeing by 2x is a parsing question, not a rounding one.**
  Line-level vs response-level accounting is exactly a factor of ~2 when
  streaming writes two lines per response. Check the unit before the maths.
- **"Are you sure?" is worth a re-derivation, not a defence.** Both the
  challenge and the original answer turned out to be half-right.
- **The expensive bug in an observability tool is attribution, not arithmetic.**
  The token maths was right the whole time. What was wrong was *which rows
  belong to the thing you named* — and that error is invisible unless you check
  a total you can predict independently.
- **Derive the boundary from causality you can prove.** `toolUseId` links a
  subagent to the exact turn that spawned it; `<tool-use-id>` back-references
  link an agent's result turn to its origin. Both are in the transcript. A
  time-window heuristic would have swallowed the next question.
- **Prefer undercounting to overcounting when you must guess** — then show the
  wall span next to it so the gap is visible.
- **Time in a transcript is derived, not recorded.** There is no latency field;
  "time" is the gap ending at a response, which is model time only — it excludes
  tool execution and human think time. Label it, or people will read it as wall
  clock.
- Deleting the duplicate implementation was the actual deliverable. The wrapper
  shrank ~170 → 60 lines by owning nothing.

### Raw material for LinkedIn / posts

- *"My cost dashboard told me a pipeline run cost $0.13. It cost $3.94. The
  arithmetic was perfect — I'd just grouped the rows by the wrong key."*
- *"A slash command's work doesn't live in the turn that started it: the human
  answers a question, four background agents report back, and you get six turns
  for one logical run. Attribution has to follow causality, not timestamps."*
- *"Two independent runs of my application pipeline, same shape: the
  orchestrator is the single most expensive agent (28%), and the render phase on
  Haiku is 0.6% of spend while producing 100% of the files a recruiter opens."*
- *"Rewrote a 170-line cost script into 60 lines by deleting the second
  implementation of parsing and pricing. Reads in 34 ms."*

## Run 5 — Company C GmbH (Laravel PHP Softwareentwickler), de
### 2026-07-25 23:09-23:22 UTC · session 8037295a

`/generate-application` end to end, both documents, one language. Twelve
renderer checks passed on the first render attempt; no retry, no page-fit loop.

### Numbers

| step | model | calls | cost | share |
|---|---|---|---|---|
| main thread (orchestrator) | opus-5 | 12 | $1.94 | 48.6% |
| generate-cv | opus-5 | 3 | $0.74 | 18.5% |
| generate-cover-letter | opus-5 | 6 | $0.72 | 17.9% |
| preparation | opus-5 | 2 | $0.58 | 14.5% |
| output-generator (render) | haiku-4.5 | 3 | $0.02 | 0.5% |
| **total** | | **26** | **$4.00** | |

1.43M tokens · 71.4k output · cache hit 83.5% · model time 13m56s · wall span
13m41s · $0.29 per minute of model time.

- **$4.00 vs $3.94 (Company B run 3) — the pipeline cost is stable to ~1.5%**
  across two different offers, two languages' worth of standards, and a
  different set of subagents doing the writing. Useful: the per-application
  cost of this pipeline is now a known quantity, not a guess.
- **Render on Haiku: $0.02, 8.3 seconds, 0.5% of spend** — and it produced all
  three files the recruiter actually opens. Third consecutive run at ~0.5%.
- The cover letter needed **6 calls to the CV's 3** — it self-checked page fit
  (`--page-check`), found 2 pages, trimmed, re-checked. Cost the same as the CV
  anyway ($0.72 vs $0.74).

### Why the orchestrator jumped 28.2% → 48.6%

Not a regression in the pipeline — a consequence of how I injected context.
`/generate-application` says to inject context file *contents*, never paths. The
standards files (branding, voice, application, CV, cover-letter) went into each
subagent prompt verbatim, so the orchestrator's **output** tokens carried them:
27.1k output on the main thread, most of it prompt text I typed for someone else
to read.

One deliberate deviation: **`profile.json` went in as an absolute path, not
inlined.** It is ~1300 lines / ~13k tokens, and three agents needed it. Inlining
would have added ~39k orchestrator output tokens (roughly +$1, a 25% run
increase) — but the decisive argument was not cost. Hand-transcribing the single
source of truth three times is a *fact-corruption* risk, and the hard rule for
these documents is "never invent facts". A path cannot mistype a date. Each
agent was told to read exactly that one file and not explore.

### Transferable lessons

- **Injected context is orchestrator output tokens.** "Inject contents, never
  paths" makes the parent pay, in the most expensive column there is. Fine for
  short prose that shapes voice; wrong for a large structured fact base.
- **Prefer a path when fidelity matters more than isolation.** Copying beats
  referencing only when you can copy losslessly. For a 1300-line JSON you
  cannot, so referencing is both cheaper *and* more accurate — the rare case
  where the efficiency rule and the quality rule point the same way.
- **The renderer owning verification paid off again.** Nothing in the writing
  phase iterated on page fit for the CV; the one trim pass happened inside the
  cover-letter agent, which had a cheap check available to it.
- **A 2-page CV that passes the page rule is not a failure.** 1045 words, page 2
  carries real content. The rule is "≥10 lines on page 2", not "one page".
- **Ask the blocking question, but only the blocking one.** Kiel is ~460 km from
  Gelsenkirchen with 3 office days a week, and nothing in the KB says she would
  relocate. One question, one answer ("don't mention it"), then both documents
  were written silent on location. Guessing either way would have wasted a
  letter.

### Honest gap this run had to handle

The posting requires **3 years of Laravel**; the truthful figure is ~1 year 5
months in production (since 03.2025) plus own Laravel projects since 2024 and
multi-year Symfony/Doctrine on top of ~7 years of professional PHP. Both
documents state the depth and never state the number. The letter places it
*after* the evidence, not in the opening — the gap is real, so the sequencing is
the only lever.

### Raw material for LinkedIn / posts

- *"Two runs of the same pipeline on two different job offers: $3.94 and $4.00.
  Once a workflow's cost is stable to 1.5%, you can budget it — and start
  arguing about whether it's worth it, which is the more interesting question."*
- *"The cheapest agent in my application pipeline costs $0.02 and produces every
  file a recruiter actually opens. The expensive ones produce text for other
  agents to read."*
- *"My orchestrator's cost share went from 28% to 49% between two runs. The
  pipeline didn't change. I'd started pasting context into subagent prompts
  instead of pointing at it — the parent pays for that, in output tokens."*
- *"I refused to inline a 1300-line JSON into three prompts. Not to save a
  dollar: because retyping your single source of truth three times is how a date
  quietly becomes wrong, and 'never invent facts' is the one rule a job
  application can't bend."*
- *"A posting wanted 3 years of Laravel. I have 1.5 in production. The letter
  says so — after four paragraphs of evidence, not in the first line. You can't
  close a gap by opening with it."*

## 2026-07-27 — Company C revision: three corrections, and where they actually belonged

Jacqueline reviewed the Company C letter and rejected three things: a
self-characterising work-style line ("und ich höre selten bei der ersten Lösung
auf, die funktioniert"), Symfony framed as multi-year experience when it is
private/volunteer only and far below full-time intensity, and the closing
paragraph naming individual side projects as work samples.

### The interesting part: two of the three were my own rules talking back

- The rejected sentence was not invented. `communication-rules.md` listed
  *"I usually continue optimizing after the first working solution."* under
  **Authentic phrasing patterns**. The generator quoted the style guide
  faithfully. Deleting the sentence from the output would have regenerated it on
  the next run.
  **Corrected an hour later:** the pattern itself is fine — Jacqueline allows
  *"…if time allows it."* What failed was the German rendering, which dropped
  the time qualifier ("ich höre selten bei der ersten Lösung auf, die
  funktioniert") and thereby reads as overengineering instead of craft. My first
  fix banned the whole pattern; the actual rule is narrower and
  language-specific: the qualifier is load-bearing, and this sentence does not
  survive translation into German unqualified. Overcorrecting a style rule
  costs a genuinely good sentence in every future English letter.
- "Mehrjährige Symfony-Erfahrung" was also not invented — it was *inferred*.
  `profile.json` says Narutorpg.de, 2009–present, Symfony/Doctrine
  modernization; the generator rounded that to multi-year professional
  experience. The fact store was right, the inference was wrong.

So the honesty bug lives in the inference step, not in the data. A note that
forbids the inference is the only fix that survives the next run:
`skills.symfony_note` plus a `meta.source_documents` correction line, mirroring
the Laravel correction from 2026-07-26.

### What changed

- `communication-rules.md`: phrasing pattern deleted, perfectionism-flavoured
  self-characterisation added to **Avoid** with the reason (unverifiable, and a
  reader can hear "never finishes").
- `cover-letter-standards.md`: never name individual side/private projects — the
  offer to bring work samples stays, the enumeration goes.
- `profile.json`: Symfony scope note + correction entry; digests rebuilt so
  generators actually see it (they read `.digest/`, not `profile.json` — a stale
  digest silently ignores a KB fix).
- Letter and CV content edited in place, `render_application.py --company
  Company C --lang de`, 12/12 checks passed (letter 501 words → 1 page, CV 2
  pages).

### Numbers

$1.10, 16 calls, 95.3 % cache hit, 0 subagents, ~7 min wall / 1m22s model time.
A full pipeline run on the same offer was $3.94–$4.00. Editing costs ~27 % of
regenerating when the facts changed but the structure did not.

Also noted: run 5's entry above still states the pre-correction Laravel figure
(~1 yr 5 mo). Left as-is — the log is a snapshot of what I believed then, not a
source of truth. `profile.json` is the only file allowed to be right.

### Raw material for LinkedIn / posts

- *"A sentence I struck from my cover letter turned out to be a direct quote
  from my own style guide. The model didn't hallucinate my voice — it obeyed my
  documentation of it. Fixing the letter without fixing the guide just schedules
  the sentence for next week."*
- *"My CV overstated my Symfony experience. The knowledge base was correct:
  volunteer project, 2009 to today. The generator turned that into 'multi-year
  experience'. Honesty bugs don't live in the facts, they live in the step that
  summarises them — so the fix is a rule that forbids the summary."*
- *"Three sentences corrected: $1.10 and no subagents. Regenerating the whole
  application: $4. Knowing which one you need is the actual skill."*
- *"Never-satisfied-with-the-first-solution is meant to read as craft. Read it
  again as a hiring manager with a deadline. Same sentence, opposite signal —
  and the four words that fix it are 'if time allows it'."*
- *"'I keep optimizing after the first working solution, if time allows it' is a
  sentence I stand behind. Its German translation, with the qualifier lost on
  the way, says overengineering. One style rule, two different answers depending
  on the language — which is exactly the kind of rule a generator will get wrong
  unless you write it down."*

## 2026-07-27 — /optimize-linkedin, DE + EN: the cheapest phase found the expensive bug

Four agents, $9.68, 47 calls, 39m15s model time / 46m wall, 90.4 % cache hit.

| phase | cost | share |
|---|---|---|
| audit (`linkedin-analyze`) | $1.30 | 13.5 % |
| writer EN | $2.88 | 29.7 % |
| writer DE | $2.62 | 27.1 % |
| orchestrator (me) | $2.88 | 29.7 % |

Caveat per this file's honesty rule: token counts, call counts and all timings
are measured; the dollar figures still rest on the estimated `claude-opus-5`
rates in `pricing.json` ($5/$25 per Mtok), so treat the ratios as solid and the
absolute dollars as approximate.

### The audit was the bargain

For $1.30 the audit found a structural defect no amount of good writing would
have fixed: the wpt-online **developer** position (06.2021–09.2024) has no
LinkedIn entry at all, only the concurrent Marketingkommunikation role. So the
profile shows a marketing job for three years and ~3 years 4 months of
primary-framework Laravel is invisible to exactly the "3+ years Laravel" filters
she genuinely passes. The two writing phases cost $5.50 together and could not
have found it — they render what the plan says.

Second-cheapest insight from the same phase: `PHP` was missing from the headline
entirely, while `Agentic Coding` occupied the first slot — the ~35 characters
that survive mobile truncation. Her only LinkedIn-verified skill badge is PHP.

### Resuming a dead agent beats re-running it

The German writer died on `API Error: Connection closed mid-response` **one
sentence before writing its file** — all thinking done, nothing on disk. Resumed
it from its own transcript with a two-line "continue from there" message: it
wrote the file and returned. A fresh spawn would have cost ~$2.60 and ten
minutes to rediscover what it already knew. The context is the expensive part of
an agent, not the tokens it emits.

### Why the orchestrator cost as much as a writer

I wrote nothing and still spent 29.7 %. The cause is prompt construction: the
three rule files are injected verbatim into every subagent prompt (the command
requires it, and it guarantees the agent follows the *current* rules). What I
refused to inline was `profile.json` (44 KB) and the audit brief (7k tokens):
the facts went in by path, and the brief was written to disk once and referenced
twice instead of pasted into both writer prompts. Inlining both would have added
roughly 20k output tokens and produced three drifting copies of the single
source of truth.

### Honesty fixes the audit forced

- `Core contributor (top-3 of a ~7-person team)` — an unmeasurable self-ranking
  with no basis in `profile.json`. Replaced by named component ownership.
- Two positions titled `AI-Assisted Web Development`, one starting **June 2021**.
  Retro-labelling a 2021 role as AI-assisted invites a plausibility question in
  public, where she does not get to answer it.
- Symfony: skills list and the community-project entry only, ranked below
  Laravel, never in the headline, never beside Laravel as an equal.

### Raw material for LinkedIn / posts

- *"The $1.30 phase found what the $5.50 phases couldn't: three years of Laravel
  missing from my own profile, because one position had no entry. Writing better
  copy would never have surfaced it — auditing structure did."*
- *"An agent died one sentence before saving its work. Resuming it from its
  transcript cost cents; restarting it would have cost $2.60 and ten minutes.
  Treat agent context as the asset, not the output."*
- *"My orchestrator spent as much as the agent that wrote a 42,000-character
  profile — and it produced no profile. Whatever you paste into every subagent
  prompt is what you're really buying."*
- *"'Core contributor, top 3 of 7' reads like a fact and is an opinion with a
  number on it. On a public profile, the reader gets to ask 'measured how?' and
  you never get to answer."*

## 2026-07-27 — self-hosted Langfuse: four traps, and where config belongs

Installed Langfuse locally (Docker, six containers) and activated Langfuse's
official Claude Code plugin. Measured, not estimated: the stack holds
**2,003 MiB** RAM, the shallow clone is **61 MB**, and of the 236 lines of
configuration only **57 are ours** (13-line port override + 44-line `.env`) —
the other 179 are upstream.

### Trap 1 — `POSTGRES_PASSWORD` is only honoured on first init

First start died on `P1000: Authentication failed against database server`. The
cause was not a typo: Docker's Postgres image applies `POSTGRES_PASSWORD` only
when it *initialises* a cluster. The compose project reused an existing volume
(`langfuse_langfuse_postgres_data`, created earlier the same day), so the freshly
generated password never matched. Renamed the project
(`COMPOSE_PROJECT_NAME=langfuse-local`) to get clean volumes instead of deleting
data whose provenance I did not know — it turned out to hold one org, user,
project and API key.

### Trap 2 — a password test that proves nothing

`docker compose exec postgres psql -U postgres` with the new password succeeded
while the app kept failing. Local socket connections use `trust` in that image:
the password is never checked. **Verify credentials over the same transport the
application uses**, or the test is theatre. This one nearly sent me looking for
a bug in the app.

### Trap 3 — a plugin can be installed and still do nothing

`claude plugin install` reported "already installed (scope: user)" — from an
earlier attempt — and then: *5 userConfig options not yet set*. So the plugin had
been sitting there tracing nothing. `--config` is only read during install and a
second install call is a no-op, so the fix was uninstall + reinstall with
`--config`. Installed ≠ configured ≠ active.

### Trap 4 — the same stack twice on one machine

A second Langfuse was already running inside the `gpos-dev` project, plus an
orphaned third volume set. Two Postgres containers on one data volume would
corrupt it; these had separate volumes, but checking the mounts before starting
anything was the only reason I knew that. Langfuse is multi-tenant by design —
one instance, one *project* per context, not one stack per repo.

### Where this config belongs — and where it does not

I first argued for versioning our 57 lines in this repo for reproducibility. Then
I read them: ports, secrets, container-internal URLs, a telemetry switch, the
headless org/user init. **Not one line references this project**, and the plugin
traces every Claude Code session on the machine regardless of directory. So it is
machine setup, not project code, and it stays out of the applications repo. The
README keeps only what is project-relevant (that tracing exists, the URL, how to
operate it, how to activate the plugin) plus pointers to where the values live —
documenting the values twice is exactly the drift that produced three of the five
pipeline defects on 2026-07-25.

### Raw material for LinkedIn / posts

- *"`POSTGRES_PASSWORD` is applied when the cluster is initialised and never
  again. Every 'authentication failed' against a container database that used to
  work is this, and no amount of re-reading your connection string will show
  it."*
- *"My password test passed while the app kept failing auth. The test connected
  over the Unix socket, where that image trusts everyone. Test over the transport
  your application actually uses, or you are testing the wrong thing."*
- *"The observability plugin had been installed for hours and traced nothing —
  five config options unset. Installed, configured and active are three different
  states, and only the last one produces data."*
- *"I almost committed 57 lines of infrastructure config into a career knowledge
  base for 'reproducibility'. Then I read them: ports, secrets, container URLs.
  Nothing about the project. Ask what a file is about before you ask where it
  should live."*

## 2026-07-31 — profiling `/generate-application`: the compute was 0.2 % of the wall clock

Asked why the pipeline takes so long. Profiled it against three recorded runs in
`~/.claude/projects/-home-jacqueline-Desktop-applications/` (orchestrator
transcripts plus the per-agent files under `subagents/`), then fixed six causes.

**The first measurement ended the search for a slow script.** The whole
deterministic output phase — CV template fill, page-fit escalation, Chromium
render, 12 verification checks — runs in **1.67 s**. A single `soffice` HTML
conversion is 0.89 s, a Chromium print 0.55 s. Every remaining minute is model
turns. So there was nothing to optimise in Python, and the entire question was
turn count and context size.

### Measured baseline — one clean run (Company B, both documents, session `6d3e6ade`)

| phase | turns | output tok | cache-read tok | span |
|---|---|---|---|---|
| orchestrator (pipeline portion) | 20 | 39,664 | 901,621 | 15.7 min |
| `preparation` | 16 | 11,772 | 456,903 | 4.8 min |
| `generate-cv` | 22 | 20,350 | 815,583 | 4.1 min |
| `generate-cover-letter` | 33 | 16,890 | 978,265 | 4.9 min |
| `output-generator` | 8 | 1,606 | 52,786 | 0.6 min |
| **total** | **99** | **90,282** | **3,205,158** | **~12–13 min machine** |

Cache-write was 428,157. Wall clock was 15.7 min including ~3.5 min of my own
answering time on two `AskUserQuestion` prompts — the two largest gaps in the
trace (286 s and 210 s) are agents running, not waiting on me. Same pricing
caveat as the 2026-07-27 entry: turns, tokens and timings are measured, the
**≈ $6.54/run** rests on the estimated `claude-opus-5` rates in `pricing.json`.

Two other runs bracket the variance: `ca686015` took **43.4 min**, and in
`00ecc276` a single cover-letter agent spent **27.1 min over 42 turns with 14
Edit calls** on one page of text, while its output phase spent **40.7 min over
41 turns**. So the pipeline was 12 → 43 min, and the spread had one dominant
cause (defect 2 below).

### Why context, not output, is the bill

A file read at turn 2 is re-sent on every later turn. `profile.json` costs
**~29,300 tokens** per read (79,344 chars over 1,311 lines, and `Read` prefixes
every line with its number). That one file therefore accounted for:

```
generate-cover-letter   29,300 × 31 later turns  =  908,300
generate-cv             29,300 × 20              =  586,000
preparation             29,300 × 14              =  410,200
                                        ≈ 1.90M of 3.21M  →  59 %
```

**Six defects, all in prompts, none in code:**

1. **Every subagent read the fact base itself, and three read it twice.** The
   orchestrator's prompts were 6,848–13,363 chars (~2–3k tokens): it was passing
   *paths*, while its own command file said to inject *contents*, while the agent
   files said "do not read context or rule files yourself." None of the three
   matched reality. In `ca686015`, `preparation`, `generate-cv` and
   `generate-cover-letter` each opened `profile.json` **twice**.
2. **The cover-letter page-fit loop was still in the agent.** `fit_cover_letter`
   in `render_application.py` has guaranteed one page since it was written, and
   its docstring says the agent loop was removed — but
   `generate-cover-letter.md` still ordered the agent to verify with
   `--page-check`. So it kept looping: 33 turns in the clean run, 42 turns and
   27.1 min in `00ecc276`. The docstring described an intent, not the system.
3. **A whole agent wrapped a 1.67 s command** — and ran on the wrong model.
   `output-generator.md` declared `model: haiku`; both run metas record
   `"model": "opus"`, because the orchestrator's `model: opus` won. It also ran
   the `ls -lh`, `grep` and file reads its own file forbade.
4. **Every subagent explored, against the hard `CLAUDE.md` rule** — `find -iname
   '*Company B*'`, `ls -la` across three directories, `git show HEAD:…`,
   `git log`, and reads of `render_application.py` (+5.5k tokens) and
   `ats_hygiene.py` inside the *cover-letter* agent. ~11 turns per run. The cause
   was structural, not disobedience: agents were given a filename pattern and no
   path, so they hunted. `generate-cv` even probed `.digest/` and found nothing
   usable.
5. **`sound-like-human-standards.md` was mandatory but unlisted.**
   `communication-rules.md:5` requires it for every generated text; the
   orchestrator's context list never named it. Agents read it anyway, by
   guessing — which is defect 4 with a good motive.
6. **`profile_digest.py` existed to solve all of this and nothing used it.**
   Written earlier with a docstring measuring the exact problem, producing
   phase-scoped minified digests (58,084–61,363 chars, ~19.4–20.5k tokens,
   36–39 % under a `profile.json` read). Zero references anywhere. Worse, the
   digests on disk were built **2026-07-28 16:20** against a `profile.json` last
   modified **2026-07-30 22:23** — two days stale, and `.digest/` is gitignored,
   so a fresh clone has none at all.

### Fixes shipped

Path-injection replaced content-injection, pointed at the phase-scoped digest;
step 3 now rebuilds the digests before any agent runs; the orchestrator renders
directly and `output-generator.md` is deleted (its "Keywords" section was a
duplicate of `application-standards.md:37`, so no rule was lost); the
`--page-check` order became an explicit prohibition; `sound-like-human-standards.md`
is now named; and `preparation` receives the `ls -1 career-kb/content/` inventory
so it picks a base JSON that exists instead of constructing a filename.

**The enforcement change is the one worth remembering.** I removed the `Bash`
tool from all three agents (`preparation` keeps `Read, WebFetch, WebSearch`; the
generators keep `Read, Write, Edit`). The old files *already* said "do not read
context files yourself" and "do not run additional checks," and the transcripts
show both instructions ignored. A capability an agent must not use is better
removed than forbidden.

### Estimated effect — NOT YET MEASURED

Projected from the per-defect measurements above; the real numbers come from the
next application run and belong in this table when they exist:

| | measured before | **estimated** after | measured after |
|---|---|---|---|
| turns | 99 | ~60 | *pending* |
| cache-read tok | 3,205,158 | ~1.3M | *pending* |
| output tok | 90,282 | ~70k | *pending* |
| cost (est. rates) | ≈ $6.54 | ≈ $2.60 | *pending* |
| wall clock | 12–13 min (43 min worst) | ~6 min, no 40-min tail | *pending* |

Treat every "after" figure as a hypothesis. The 59 % share of cache-read traced
to one file is measured; that removing it converts linearly into wall clock is
not.

### Transferable lessons

- **Measure the deterministic part first, to rule it out.** One 1.67 s timing
  redirected the entire investigation away from Python and toward prompts.
- **A docstring that says a problem is solved is a claim, not evidence.**
  `render_application.py` documented removing the fit loop; the agent file still
  ordered it. Both files were internally consistent and the system was not.
- **Dead tooling is worse than missing tooling.** `profile_digest.py` was
  correct, measured, and unreferenced — so the cost it was built to remove was
  paid in full every run, and its stale output was a live correctness risk.
- **Three files disagreed about one decision and the code obeyed none.** Inject
  contents / do not read files / read them anyway. Contradictions do not
  resolve, they get resolved by whichever agent runs.
- **Content-injection is the expensive direction.** Pasting the fact base into
  three prompts means ~100k *output* tokens — the slowest and dearest class — to
  move data a subagent reads for a fraction of that. Paths win by ~20×.

### Raw material for LinkedIn / posts

- *"My slow AI pipeline spent 1.67 seconds in code and 13 minutes in model
  turns. I had been planning to optimise the Python. Measure the part you can
  measure exactly first — if only to eliminate it."*
- *"One 79 KB JSON file was 59 % of my pipeline's token bill. Not because it was
  read too often — because it was read at turn 2 and re-sent on all 31 turns
  after it. In agent systems, what you load early you pay for repeatedly."*
- *"I found a tool in my own repo that solved my exact bottleneck, with the
  measurements in its docstring, referenced by nothing. Its cached output was
  two days stale. Unused correct code is not neutral; it is a bill you pay plus
  a wrong answer waiting."*
- *"Three files in my pipeline disagreed about one decision: the orchestrator
  said inject the data, the agents said never read the data, and the agents read
  it twice. Every file was internally consistent. The system was incoherent."*
- *"My agents kept ignoring 'do not run extra checks', so I took away their
  shell. Instructions are a request; tool grants are the actual policy."*
- *"A docstring in my renderer said the expensive edit loop had been moved into
  code. It had. The agent prompt telling the model to do it manually was still
  there — 27 minutes and 14 edits on one page of text."*

## 2026-07-28 → 07-31 — the fact base got stricter: gender, money, and what is *not* RAG

Catch-up on four days that produced no entry. Mostly knowledge-base work, and
the corrections are the valuable part.

### Two hard rules that change every future document

- **Grammatical gender (2026-07-30, `communication-rules.md`).** She is a woman;
  every text about her uses the **feminine** form in every language that marks
  it — "Softwareentwicklerin", "Entwicklerin", "Werkstudentin", "Mentorin". Never
  the generic masculine, and never a neutralising dodge ("Person mit Erfahrung in
  …"). `Entwickler:in` forms belong to *postings addressing a group*: quoting an
  advertised title verbatim is correct, writing about herself in it is not.
- **Money, dates, relocation (2026-07-30, `application-standards.md`).** Never
  volunteer a salary expectation or a start date; if a posting asks, **ask her
  for the figure** rather than deriving one. `"ab sofort verfügbar"` counts as a
  start-date statement and goes out with the rest. Relocation is **no, ever** —
  and it is never framed as a limitation, per *Never frame by negation*.
  `preparation` now stops on offers requiring on-site work outside NRW, with
  exceptions only for a bounded period (onboarding) or remote-possible postings;
  more than 2 on-site days a month is a hard stop.

### What she does and does not have (2026-07-31, Company D posting)

- **MCP: upgraded.** She has *built* an MCP client/integration into her own agent
  workflows, so "MCP-Client integriert" is licensed — but she named no project,
  so no project name may be attached. State the capability, not a location.
- **TypeScript: downgraded to honest.** She writes some Capacitor/TypeScript
  terminal code at Gastro IT, occasionally, not as a focus. That plus the React
  18/TypeScript take-home is the whole evidence base. It never supports a
  "4 years of TypeScript" claim.
- **RAG, embeddings, vector databases: none.** They stay in
  `role_skill_map.must_learn` and may appear once, in prose, as "baue ich gerade
  auf".
- **Knowledge graphs: none.** Her answer was "yEd, mermaid" — *diagramming*
  tools. They license Neo4j, Cypher, RDF/SPARQL and "Knowledge Graph" not at all.
  The term leaves the documents with no disclaimer.
- Java stays absent. English stays "fließend" — no C1 claim, no certificate.
- `PhpSpreadsheet` was removed from the skills list and from the Sanctum project
  in both `php-developer` base JSONs.
- GitHub Copilot may be named (private and occasional Gastro IT use), but never
  headlines the AI positioning — Claude Code is the primary practice. Cursor is
  still not hers.

**The most useful correction is self-referential.** She asked whether this
pipeline counts as RAG. It does not: no retriever, no embeddings, no vector
index, no chunking, no similarity search — nothing is *retrieved*. What it
genuinely is: **context engineering** plus a **multi-step agent workflow with
orchestration** — an orchestrator command, specialised subagents, a
single-source-of-truth knowledge base, and a deterministic verification step in
`render_application.py`. That is the honest label, and it is the concrete
artefact behind "Designed agent workflows" and "Context management" in the AI
Engineering Experiments project.

One consequence to carry into `profile.json`: that note describes the pipeline as
injecting facts "wholesale into subagents", which the 2026-07-31 rework above
replaced with path-injected, phase-scoped digests. Still not RAG — even less so —
but the description is now stale, and the *new* architecture is the better
evidence: pre-scoped context digests with measured token accounting.

### Verified Gastro IT facts, and the corrections behind them

`profile.json` gained 152 changed lines, mostly verification against the actual
repo rather than recollection:

- API credentials are **Sanctum**, not JWT — with the reason recorded: tokens must
  be long-lived, revocable and DB-backed; JWTs are hard to revoke, Passport
  OAuth2 was overkill. A design decision with a rationale is CV material; a
  technology name is not.
- **~50 models** exposed as `#[ApiResource]`, and the resources that may be named
  as examples of that scale are now listed (Menükarten, Produkte, Standorte,
  Terminals, Zahlungsmethoden, Drucker) — because [[examples-give-numbers-scale]]:
  "~50 resources" needs one real name beside it.
- **Five** legally critical models (BusinessTransaction, BusinessTransactionEvent,
  ChangeLog, PrintJob, Language) are read-only over the API as a KassenSichV
  guard, so a POST cannot bypass event-sourcing and TSE signing.
- The feature is **built and in review, not merged**. Never "in production", and
  there is **no tenant count** because it is not productive yet.
- Tests: **58 test classes** — 48 inheriting a CRUD base defining 18 cases per
  resource, 4 inheriting a role-permission base with 2 each. The number of
  *executed* cases was never measured, so the class count and cases-per-resource
  may be stated and a derived total may not.
- Corrections: **Pest and Selenium are not her work** in that role. **She did set
  up the self-hosted Langfuse herself**, so "aufgesetzt" is licensed — but not
  "introduced LLM observability at the company". OAuth in the skills list is
  genuinely **OAuth2**, from the Facebook API integration at wpt-online.
- The **ticketing system** is not the Laravel application: a genuinely legacy
  system of glued-together parts grown over **20+ years** (XSLT, Vue.js, raw
  HTML, Bootstrap, CSS, MySQL). So wpt-online does carry professional legacy
  evidence, the 80 % load-time result should carry that context, and only the
  ~3-year-old Laravel codebase must never be called legacy.

### Two housekeeping lessons

- **`sound-like-human-standards.md` was created** (+37 lines) to hold the
  `Human_Writing_Ruleset.pdf` rules — buzzword and stock-phrase blacklists,
  hedging ban, rhythm and sentence-opening variation, editing checklist. It
  governs *whether text reads as human*; `communication-rules.md` governs *what
  the voice says*. Splitting them was right, and the rework above shows the cost
  of the split: a mandatory file that no pipeline stage was told to load.
- **~40 MB of generated `.docx`/`.pdf` left git** (commit `e4ccb92`, 697
  deletions): per-company outputs and all sixteen `base-cvs` artifacts. They are
  reproducible from `content/*.json` plus a template in 1.67 s. A knowledge base
  stores facts and generators, never their output.

### Raw material for LinkedIn / posts

- *"'~50 API resources' means nothing until one of them is 'Menükarten'. A count
  without an example is a number the reader cannot picture — so give the scale
  and one real thing at that scale."*
- *"I asked whether my own agent pipeline was RAG. No retriever, no embeddings,
  no vector index, nothing retrieved. It is context engineering and workflow
  orchestration. Using the fashionable word would have cost me the first
  technical follow-up question in an interview."*
- *"Sanctum over JWT because the tokens had to be long-lived, revocable and
  DB-backed, and revoking a JWT is the hard part. The decision is the
  engineering; the library name is just where it landed."*
- *"Five models in that API are read-only, so no POST can bypass event-sourcing
  and TSE signing. In German fiscal software the interesting design work is
  usually what you make impossible."*
- *"I deleted 40 MB of generated PDFs from my knowledge base. They rebuild in
  1.67 seconds from the JSON that was already there. If you can regenerate it,
  it is output, not knowledge."*
- *"My CV said 58 test classes at 18 cases per resource, and not the product of
  those two numbers — because nobody ever ran the count. The multiplication
  would have been true-looking and unverified, which is the same as false."*

## 2026-07-31 — Run: Company D (posted as "Company D alias") — Software Developer, RAG / Knowledge Graph / Agentic Systems, de

### Numbers
- Offer requirements: 7 qualifications, 8 responsibilities. Genuine DIRECT match on 5 of 7
  qualifications; **3 hard gaps**: RAG/embeddings/vector DBs, graph technologies, Java.
- The formal bar "4+ years in Java, Python or TypeScript" is **not met in any single one of the
  three named languages**. What is genuinely ≥4 years: professional development since 2019-08
  (≈6 years 7 months) and PHP/Laravel (≈4 years 9 months production, written as "ca. 5 Jahre").
- Documents: CV 2 pages / 932 words, cover letter 1 page / 532 words (body 494). 12/12 renderer
  checks passed, first try, scale 1.0, 0 bullets dropped.
- Evidence kept: 6 Gastro IT bullets, 5 wpt-online bullets, 4 projects. Dropped for relevance,
  not honesty: starter-kit/SEO/Barrierefreiheit/DSGVO, the ~10 target terms, Facebook/OAuth2 as a
  bullet, standalone DB design, the book, the LinkedIn brand, the OSS fork as a standalone entry.
- 4 clarifying questions asked before generating; 2 of the 4 answers had to be **corrected**
  rather than used.

### Why
- **Two of my own answers were the wrong answer, and saying so was the value.** "Does importing
  LinkedIn/PDF/GitHub data into my KB count as RAG?" — no: no retriever, no embeddings, no index,
  nothing retrieved. "Graph technologies? yEd, mermaid" — no: those draw diagrams, a knowledge
  graph is a queryable structure with traversal. Both would have been *plausible* on paper and
  both die in the first technical follow-up. The posting accepted "a strong motivation to work
  with" these, so the honest version cost almost nothing and the dishonest version risked
  everything.
- **The gap belonged in the middle of the summary, not at the end.** The CV summary first ended on
  "RAG und Vektordatenbanken baue ich gerade auf." Final position is the most-remembered slot in a
  paragraph; spending it on the one thing I cannot do yet inverts the whole document. Moved it
  inward, ended on payment-critical data and TSE/KassenSichV instead. Same sentences, same
  honesty, different last impression.
- **A confirmed capability outranks a cautious one — once it is confirmed.** The KB said "works
  with MCP". I have actually built an MCP client/integration, and MCP clients are a literal line
  item in the posting. Recording that in `profile.json` upgraded a hedge into a match. The
  opposite of overstating is not understating; it is asking.
- **The non-obvious argument beat the obvious one.** Company D does payments, BNPL and debt
  reduction. Nothing in the posting asked for fiscal or payment experience — but Mahnungen,
  bank-transfer import/export, TSE/KassenSichV and "five models are read-only so no POST bypasses
  event-sourcing" say more to a FinTech about whether my agents will survive contact with their
  domain than another paragraph about prompts would.
- **Mixed-language posting: mirror the employer, not the reposter.** German company copy (du,
  first person), English recruiter boilerplate (third person about Company D, "Knowledgraph"
  misspelled twice). German won, because the German text is the only part Company D demonstrably
  wrote and the posting demands German at C1+ — a German document evidences that in the medium
  itself. No ATS cost, since the English technical terms go in either way.

### Post angles
- *"The job wanted RAG. I asked my own assistant whether my knowledge-base pipeline counted, and
  it said no — no retriever, no embeddings, nothing retrieved. It was right. I applied anyway,
  with the gap named once and the adjacent skills named properly. Reaching for the fashionable
  word is how you lose the first interview question."*
- *"yEd and Mermaid draw graphs. A knowledge graph is queried. Not the same noun."*
- *"The posting asked for 4 years of Java, Python or TypeScript. I have none of those at 4 years —
  I have six years of shipping software and five of Laravel in production. I wrote that, plainly,
  instead of adding three part-time numbers together until they cleared the bar."*
- *"I moved one sentence in my CV and changed nothing else. It was the sentence about what I
  cannot do yet, and it had been sitting in the last line. Last line is what people remember."*
- *"Their posting never asked about payments. My best argument was Mahnungen and TSE signing.
  Read what the company does, not only what the job ad lists."*
