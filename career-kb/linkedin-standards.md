# LinkedIn Profile Standards

Channel-specific rules for Jacqueline Urban's LinkedIn **profile**. Inherits the
universal branding (`general-standards.md`) and voice (`communication-rules.md`);
for LinkedIn *posts*, follow `social-media-standards.md`. Sources:
`Professional_Branding_Standards.pdf` (Group B), `LinkedIn_Profile_Standards.pdf`.

**What is deliberately not here:** positioning, target roles, AI positioning,
evidence-over-claims, engineering philosophy and the target impression are true
for every channel and are defined once in `general-standards.md`; writing style,
tone and the avoid-list live in `communication-rules.md` — including the form of
every position and project bullet (*Bullet points*) and the rule that About stays
flowing prose (*The person description stays prose*). What a bullet is *about* is
selected via `application-standards.md`, *Project Description Standard*. This file
only holds what is specific to the LinkedIn profile.

## Goal
- The profile has to read as an experienced software engineer with an architecture background **whose current focus is AI engineering** — arrived, not on the way. AI leads (`general-standards.md`, *AI positioning*); the architecture and PHP/Laravel depth is what makes it credible rather than trend-following.
- It must support applications for the target roles (`general-standards.md`) as they stand, without being rewritten per role.

## Section-by-section, not document-wide
- The universal writing-style rules apply to **every section separately** — headline, About, each position, projects, skills. LinkedIn is read in fragments and out of order, so a recruiter who opens only one position must still get the positioning from it.

## Field limits and mechanics (verified 2026-07-28)
- Headline **220 characters**; About **2,600 characters**.
- Skills: **100 maximum** — not 50. Never write "check the limit in the UI"; the number is known.
- **5 pinned top skills**, not 3 (Jacqueline, 2026-07-28). They are what the profile card shows before "Show all", so they carry the positioning on their own.
- **A pinned skill and a per-position attachment are claims about that entry, not about the profile.** The five pins are read as "this is what she is"; an attached skill is read as "this is what she did *there*". So a pin needs evidence somewhere in the profile, and an attachment needs evidence *in the position it hangs on* — the discipline the whole entry is built on, not a term that merely appears in its context (Jacqueline, 2026-07-29: "Software Architecture" pinned and attached to Gastro IT overstated a role that is AI integration, API and backend work; `general-standards.md`, *Never upgrade the role she had*). Attach the owned components instead — Multi-Tenancy, Event-Driven Architecture — and leave the broader term further down the list where it still ranks.
- **The bullet marker is part of the pasted text** (Jacqueline, 2026-07-30). LinkedIn's description fields are plain text with no list formatting, so every work bullet in a position or project description starts with a typed `• ` — otherwise the index collapses into a block of lines and the scan advantage is gone. Applies to the description fields only: About and the volunteering descriptions stay prose (`communication-rules.md`, *The person description stays prose*), and instruction lines in the output file ("Kenntnisse anhängen", "Beschreibungsfeld") are not profile text. No equivalent rule exists for the CV — its template draws the markers.
- Skills can be attached to individual positions (and to education and certificates), which raises that skill's weight in search — but **only 5 per position** (verified 2026-07-28). That makes the per-position list a priority decision, not an enumeration; never emit more than five. Attaching is a separate step in the UI and is easy to miss.

## Discoverability
- Recruiter search ranks on **semantic relevance, not keyword matches**: the same term has to recur coherently across headline, About, position texts and skills. A term that appears once, in a list, ranks worse than one carried by a sentence that shows the work. **Keyword stuffing is penalised** — this is the LinkedIn counterpart to the ATS rule in `application-standards.md`, which does not apply here because a profile is not written per posting.
- **Verified skill badges rank noticeably higher** for that skill, and the badge only renders when the skill is in the list — so a skill with a passed assessment stays in the list even when it costs a slot.
- **Endorsements move the ranking** on skill searches. Asking the team to endorse the pinned skills is worth more than adding further skills.
- **Completeness and activity both feed visibility**: unfilled sections and months of silence cost reach. Recommendations are the strongest missing block, because they are the only third-party evidence on the platform.

## Recommendations about the GitHub profile
- The profile links GitHub, so the repos are part of it. When a repo would damage the impression if someone opened it, say so **and say what to do with it** — archive, set private, or **delete** (Jacqueline, 2026-07-28). Listing it as "deliberately not included" is not enough; a reader can still find it.
