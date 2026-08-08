# Universal Claude Instructions

Project-independent instructions, copied verbatim from the sources noted.

## From CLAUDE.md (project)

## Efficiency-first execution
- Choose the lowest-token approach (model, agents, workflow, read/generate amount).
- Deviate only when the cheaper option loses more than 25% quality.

## No exploring — ever (hard rule)
- Never explore the filesystem unless explicitly instructed. No `ls`, `find`, `glob`, `git show`, `git log`, grepping, browsing, reading unspecified files, inspecting previous outputs.
- If a required path is missing, stop and name it. Do not work around prompt bugs.

## Injected paths (subagents)
- Read each injected path exactly once and read nothing else.
- Never re-read the fact digest, and never read `career-kb/profile.json` when a digest is injected.


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
Pick the cheapest model that meets the quality bar (price per 1M tokens):
- **Haiku 4.5** ($1 / $5) — mechanical work: presence checks, grep, bulk read/extract/triage, formatting. Not multi-file reasoning.
- **Opus 4.8** ($5 / $25) — default for reasoning: tracing across `career-kb/`, verification, code review, and anything reaching an employer (`career-kb/profile.json`, `career-kb/content/*.json`, rendered CV and cover letter).
- **Fable 5** ($10 / $50) — one hard or orchestrating agent only: long autonomous runs, difficult first-shot builds, sub-agent coordination. Never for bulk verification: it is 2× Opus, slower, and false-positives.

## Hallucination reduction
- Take facts about [applicant] from `career-kb/profile.json` and `career-kb/content/`, never from memory.
- If a fact is missing there, ask. Never guess.

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
