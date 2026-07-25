---
description: Analyze and optimize Jacqueline Urban's LinkedIn PROFILE (not posts) for recruiter discoverability, trust and multi-role fit. Produces a copy-paste-ready, keyword-optimized profile as a .txt. Orchestrates the linkedin-analyze and linkedin-optimize subagents and injects the relevant context into each.
model: opus
---

# /optimize-linkedin — LinkedIn profile optimization (orchestrator)

You are the **orchestrator**. Do NOT do the audit/writing yourself — dispatch each phase to its subagent (Task tool) and **inject** the relevant context into that subagent's prompt. This command is the ONLY place that references contexts and subagents; the subagents never read the context files themselves.

## Goal
A completely optimized, keyword-rich, **honest** LinkedIn profile that yields: more recruiter findings for the target roles, more trust, and more discoverability overall. **Comprehensive** — list ALL genuine positions + strong projects + the full skills list (top-3 pinned); exclude noise (empty scaffolds, non-own clones). Optimize for as MANY target roles as possible via one multi-role umbrella (headline / About / skills); prioritize the most important (AI + architecture direction; PHP as keyword baseline).

## Contexts (the ONLY place these are referenced — inject the RELEVANT ones per phase)
Read these and pass their content into the subagent prompts (do not just pass paths).
- **Main context (inject into both phases):** `career-kb/profile.json` (only source of facts), `career-kb/general-standards.md` (universal branding), `career-kb/communication-rules.md` (voice)
- **LinkedIn context (inject into both phases):** `career-kb/linkedin-standards.md`
- (`career-kb/social-media-standards.md` is for POSTS — not used in profile optimization.)

## Subagents (referenced only here)
`linkedin-analyze` → `linkedin-optimize`.

## Steps
1. **Analyze.** Spawn `linkedin-analyze`, injecting the **Main + LinkedIn context**. Capture its optimization brief (keyword strategy, multi-role umbrella, what to include, skills plan, gaps, honesty fixes).
2. **Optimize.** Spawn `linkedin-optimize`, injecting the **Main + LinkedIn context + the brief**. It writes `career-kb/output/LinkedIn_Profile_optimized.txt`.
3. **Present** the .txt path and a short changelog (what changed + why it improves discoverability/trust) to the user.
