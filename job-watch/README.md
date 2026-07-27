# job-watch

Polls LinkedIn, Indeed and StepStone for the target roles, keeps each posting
**verbatim**, and notifies once per offer. Output drops straight into
`/generate-application`.

- **CLI reference:** `.venv/bin/python watch.py --help` (the docstring in
  `watch.py` is the only definition).
- **Queries, sources, notification channels:** `config.json`.
- **Dedupe and text-fidelity semantics:** docstrings on `dedupe_key`,
  `alias_key` and `html_to_text` in `watch.py`.

## Why scraping and not APIs

None of the three has a usable public jobs API: LinkedIn's is partner-only
(Talent Solutions), Indeed shut its publisher API down, StepStone has none and
answers `403` on its internal one. What does work, verified 2026-07-25:

| Source | Route | Full posting text? |
|---|---|---|
| Indeed | JobSpy (internal GraphQL) | yes — median ~3,900 chars |
| LinkedIn | JobSpy over the unauthenticated `jobs-guest` endpoints | yes — needs `linkedin_fetch_description` |
| StepStone | search HTML → detail page → schema.org `JobPosting` | yes — median ~3,500 chars |

There is no free API to *submit* an application to any of them — every ATS apply
endpoint needs the employer's credentials. This tool therefore ends at "here is
the offer, verbatim"; sending stays manual.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Add a notification channel to the `notify` list in `config.json` (`#`-prefixed
entries are ignored). Simplest is [ntfy](https://ntfy.sh): install the app, pick
a hard-to-guess topic, use `ntfy://your-topic-here`. Secrets stay in the
environment and are referenced as `${VAR}`.

## Cron

```cron
0 8,13,18 * * * cd [path to this repo]/job-watch && .venv/bin/python watch.py >> watch.log 2>&1
```

Three times a day is plenty and stays clear of LinkedIn's rate limiting, which
kicks in around the 10th result page from one IP.

## Caveats

- **This is scraping.** Fine for personal, low-volume use at this cadence; it is
  against LinkedIn's and Indeed's ToS, and selectors break when they redesign. A
  source suddenly returning 0 hits is the usual symptom.
- **Result churn is normal.** The boards rotate rankings, so a run minutes later
  still surfaces genuinely new postings — that is the board, not a dedupe fault.
- `glassdoor` and `google` also work via JobSpy; add them to `sources`. Google
  was raising a library-internal error at the time of writing. A failing source
  is logged and skipped, never fatal.
