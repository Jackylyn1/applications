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
