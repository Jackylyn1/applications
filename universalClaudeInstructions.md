# Universal Claude Instructions

Project-independent instructions, copied verbatim from the sources noted.

## From CLAUDE.md (project)

## Efficiency-first execution
- Always choose the **lowest-token approach** (model, agents, workflow, read/generate amount) unless it reduces quality by **>25%**. If it's within ~25% of the best, use the cheaper option.
## No exploring — ever (hard rule)
**Never explore the filesystem unless explicitly instructed.** No `ls`, `find`, `glob`, browsing, reading unspecified files, or inspecting previous outputs.
If a required path isn't provided, **stop and say what's missing**. Don't work around prompt bugs.
Exploration increases context size and cost because every later call re-reads it. It also risks pulling unrelated content into the task. Stay within the specified paths.

## From /home/jacqueline/.claude/RTK.md

# RTK - Rust Token Killer

**Usage**: Token-optimized CLI proxy (60-90% savings on dev operations)

## Meta Commands (always use rtk directly)

```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering (for debugging)
```

## Installation Verification

```bash
rtk --version         # Should show: rtk X.Y.Z
rtk gain              # Should work (not "command not found")
which rtk             # Verify correct binary
```

⚠️ **Name collision**: If `rtk gain` fails, you may have reachingforthejack/rtk (Rust Type Kit) installed instead.

## Hook-Based Usage

All other commands are automatically rewritten by the Claude Code hook.
Example: `git status` → `rtk git status` (transparent, 0 tokens overhead)

Refer to CLAUDE.md for full command reference.

## From CODING_RULES.md

# AI Code Generation Rules

- Follow: KISS, YAGNI, DRY.
- Apply SOLID only when it improves maintainability.
- Apply Clean Code principles: prioritize readability, clarity, and maintainability.

## Implementation

- Implement only requested functionality.
- Use existing architecture, patterns, conventions, and dependencies.
- Prefer extending existing code over parallel solutions.
- Keep changes minimal and focused.
- Avoid unnecessary abstractions.
- Avoid premature optimization.
- Do not add dependencies without requirement.
- Do not refactor unrelated code.
- Do not introduce patterns without clear need.

## Code Quality

- Use clear, descriptive names.
- Keep functions focused.
- Prefer simple control flow.
- Use type hints where useful.
- Handle errors explicitly.
- Add comments only for non-obvious decisions or constraints.
- Group related comments instead of many small comments.

## Do Not

- Build for hypothetical requirements.
- Create unnecessary classes, interfaces, factories, services, or wrappers.
- Redesign existing architecture.
- Perform broad cleanup.

## Validation Workflow

- Run: Ruff.
- Run: Ruff Formatter.
- Run: mypy.
- Run: Bandit.
- Run: Radon/Xenon.
- Run: Vulture.
- Run: pytest + coverage.py.
- Run: pip-audit.

## Fix Workflow

- Fix only reported issues.
- Preserve behavior.
- Avoid unrelated refactoring.
- Keep changes minimal.

## From CLAUDE.md (project) — project-specific paths, adapt before reuse

## Model selection
Choose the cheapest model that meets the quality bar (per 1M tokens):
- **Haiku 4.5** ($1 in / $5 out) — mechanical work: presence/absence checks, grep, bulk read/extract/triage, formatting. Use for "look and confirm," not multi-file reasoning.
- **Opus 4.8** ($5 / $25) — default for substantive reasoning: tracing across `career-kb/` (profile, content, standards, tools), verification, code review, and anything where a wrong fact reaches an employer (`career-kb/profile.json`, `career-kb/content/*.json`, the rendered CV and cover letter).
- **Fable 5** ($10 / $50) — only for a single hard/orchestrating agent: long autonomous runs, difficult first-shot builds, frontier reasoning, or coordinating sub-agents (e.g. `/generate-application`, `/optimize-linkedin`). **Never** for bulk verification; it's 2× Opus, slower, and can false-positive.
## Hallucination reduction
If you don't know a relevant fact, say so and ask instead of guessing. Facts about [applicant] come from `career-kb/profile.json` and `career-kb/content/`, never from memory — if they aren't there (e.g. team size, a project detail, a date), ask.
## Verification belongs to the renderer, not the generator
`career-kb/tools/render_application.py` already handles page fit, dash hygiene, email replacement, filenames, and failure checks. Do **not** duplicate those checks or iterate to fit a page. The `preparation` and `generate-documents` subagents write their JSON once to the specified path and stop; merging, HTML assembly and PDF rendering belong to the renderer.
## Coding rules — read only for permanent code
Before creating or changing **permanent** code (anything committed to the repo or kept after the run — `career-kb/tools/`, `tests/`, `.claude/scripts/`, `Makefile`), read `CODING_RULES.md` and follow it.
**Do not read it** for throwaway code: scratchpad scripts, one-off shell/Python snippets, temporary files deleted after the run. Those are exempt from the ruleset.
## Document a rule at the highest context that fits — never lower
Every rule exists in exactly one file: the **most general** one in which it is still true. If it holds for every channel, it goes into the universal files (`career-kb/general-standards.md` for branding/positioning, `career-kb/communication-rules.md` for voice) and **never** into `career-kb/cv-standards.md`, `career-kb/cover-letter-standards.md`, `career-kb/linkedin-standards.md` or `career-kb/social-media-standards.md`. A rule only belongs in a channel file if it is *false* for the other channels. Channel files reference the general rule instead of restating it, and when a new source document repeats a universal rule, add nothing but the source reference.
