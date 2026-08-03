---
description: Analyze and optimize [applicant]'s LinkedIn **profile** (not posts) for recruiter discoverability, trust, and multi-role fit. Produces copy-paste-ready, keyword-optimized `.txt` files by orchestrating the `linkedin-analyze` and `linkedin-optimize` subagents.
model: opus
---
# /optimize-linkedin — LinkedIn profile optimization (orchestrator)
You are the **orchestrator**. Never audit or write yourself—delegate every phase to subagents (Task tool) and **inject** the required context into each prompt. Only this command references context files and subagents.
## Goal
Create a fully optimized, keyword-rich, **honest** LinkedIn profile that maximizes recruiter discoverability, trust, and multi-role fit. Include all genuine roles, strong projects, and the complete skills list; exclude empty scaffolds and non-own clones. Pin counts, field limits and attachment limits are defined once in `career-kb/linkedin-standards.md` — never restate a number here, it drifts out of date. Optimize under one multi-role umbrella (headline/About/skills), prioritizing AI + architecture while keeping PHP as a baseline keyword.
## Contexts
Read these files and inject their **contents** (never paths).
- **Main (both phases):** `career-kb/profile.json` (facts), `career-kb/general-standards.md` (branding), `career-kb/communication-rules.md` (voice)
- **LinkedIn (both phases):** `career-kb/linkedin-standards.md`
- **Bullet content selection (both phases):** `career-kb/application-standards.md` → *Project Description Standard* only. Bullet **form** is universal and lives in `communication-rules.md` (*Bullet points*); About stays prose per the same file (*The person description stays prose*).
- Ignore `career-kb/social-media-standards.md` (posts only).
## Subagents
`linkedin-analyze` → `linkedin-optimize`
## Steps
1. Spawn `linkedin-analyze`, injecting **Main + LinkedIn context + language**. Capture its optimization brief (keyword strategy, role umbrella, content, skills, gaps, honesty fixes).
2. Spawn `linkedin-optimize` twice (German and English), injecting **Main + LinkedIn context + brief + language**. Write `career-kb/output/LinkedIn_Profile_optimized_[language].txt`.
3. Return both `.txt` paths and a brief changelog explaining what changed and why it improves discoverability and trust.