## Efficiency-first execution
- Always choose the **lowest-token approach** (model, agents, workflow, read/generate amount) unless it reduces quality by **>25%**. If it's within ~25% of the best, use the cheaper option.
## Model selection
Choose the cheapest model that meets the quality bar (per 1M tokens):
- **Haiku 4.5** ($1 in / $5 out) — mechanical work: presence/absence checks, grep, bulk read/extract/triage, formatting. Use for "look and confirm," not multi-file reasoning.
- **Opus 4.8** ($5 / $25) — default for substantive reasoning: multi-file tracing, verification, code review, and legal/financial-critical work (TSE, DSFinV-K, LegalSignature).
- **Fable 5** ($10 / $50) — only for a single hard/orchestrating agent: long autonomous runs, difficult first-shot builds, frontier reasoning, or coordinating sub-agents. **Never** for bulk verification; it's 2× Opus, slower, and can false-positive on security-adjacent code.
## Hallucination reduction
If you don't know a relevant fact, say so and ask instead of guessing (e.g. my code review experience or team size).
## No exploring — ever (hard rule)
**Never explore the filesystem unless explicitly instructed.** No `ls`, `find`, `glob`, browsing, reading unspecified files, or inspecting previous outputs.
If a required path isn't provided, **stop and say what's missing**. Don't work around prompt bugs.
Exploration increases context size and cost because every later call re-reads it. It also risks pulling unrelated content into the task. Stay within the specified paths.
## Verification belongs to the renderer, not the generator
`render_application.py` already handles page fit, dash hygiene, email replacement, filenames, and failure checks. Do **not** duplicate those checks or iterate to fit a page. Write the document once to the specified path and stop.
## Measuring cost
Don't ask the model what a run cost—it bloats the session context. Run `.claude/scripts/cost-report.sh` instead; it reads the same transcripts with essentially no cost. Scope it with `--command <name>` (last run), `--session <id>`, `--agent <id>`, `--all`, `--today`; change row granularity with `--by step|turn|run|command|agent|model|session|call`.