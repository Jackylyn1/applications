# LinkedIn Profile Standards

Channel-specific rules for [applicant]'s LinkedIn profile. Inherits universal branding (`general-standards.md`) and voice (`communication-rules.md`). For LinkedIn posts follow `social-media-standards.md`. Sources: `Professional_Branding_Standards.pdf` (Group B), `LinkedIn_Profile_Standards.pdf`.

Deliberately not here: positioning, target roles, AI positioning, evidence-over-claims, engineering philosophy and target impression (`general-standards.md`); writing style, tone, the avoid-list, bullet form (*Bullet points*) and the prose rule for About (*The person description stays prose*) (`communication-rules.md`); what a bullet is about (`application-standards.md`, *Project Description Standard*).

## Goal
- The profile reads as an experienced software engineer with an architecture background whose current focus is AI engineering — arrived, not on the way. AI leads; the architecture and PHP/Laravel depth makes it credible rather than trend-following.
- It supports applications for the target roles as it stands, without a rewrite per role.

## Section-by-section, not document-wide
- The universal writing-style rules apply to every section separately: headline, About, each position, projects, skills. LinkedIn is read in fragments and out of order, so a recruiter who opens one position must still get the positioning from it.

## Field limits and mechanics (verified 2026-07-28)
- Headline 220 characters; About 2,600 characters.
- Skills: 100 maximum, not 50. Never write "check the limit in the UI"; the number is known.
- 5 pinned top skills, not 3. They are what the profile card shows before "Show all", so they carry the positioning alone.
- **A pinned skill and a per-position attachment are claims about that entry, not about the profile.** The five pins read as "this is what she is"; an attached skill reads as "this is what she did there". A pin needs evidence somewhere in the profile; an attachment needs evidence in the position it hangs on — the discipline the entry is built on, not a term that merely appears in its context (`general-standards.md`, *Never upgrade the role she had*). Attach the owned components — Multi-Tenancy, Event-Driven Architecture — and leave the broader term further down the list, where it still ranks.
- **The bullet marker is part of the pasted text.** LinkedIn description fields are plain text with no list formatting, so every work bullet in a position or project description starts with a typed `• `. Otherwise the index collapses into a block of lines. Description fields only: About and volunteering descriptions stay prose, and instruction lines in the output file ("Kenntnisse anhängen", "Beschreibungsfeld") are not profile text. The CV needs no equivalent rule; its template draws the markers.
- Skills can be attached to positions, education and certificates, which raises that skill's search weight — but only 5 per position (verified 2026-07-28). Treat the per-position list as a priority decision and never emit more than five. Attaching is a separate UI step and easy to miss.

## Discoverability
- Recruiter search ranks on semantic relevance, not keyword matches: the same term has to recur coherently across headline, About, position texts and skills. A term appearing once in a list ranks worse than one carried by a sentence that shows the work. Keyword stuffing is penalised. The ATS rule in `application-standards.md` does not apply here, because a profile is not written per posting.
- Verified skill badges rank noticeably higher, and the badge renders only while the skill is in the list. A skill with a passed assessment keeps its slot.
- Endorsements move skill-search ranking. Asking the team to endorse the pinned skills beats adding further skills.
- Completeness and activity both feed visibility: unfilled sections and months of silence cost reach. Recommendations are the strongest missing block, being the only third-party evidence on the platform.

## Recommendations about the GitHub profile
- The profile links GitHub, so the repos are part of it. When a repo would damage the impression, say so and say what to do with it: archive, set private, or delete. Listing it as "deliberately not included" is not enough — a reader can still find it.
