---
description: Write a LinkedIn **post** (not the profile) from a topic or experience, following the social-media standards. Produces a copy-paste-ready `.txt` in German and English.
model: opus
---
# /linkedin-post — LinkedIn post writing
Write the post yourself; no subagents. Input is the topic, experience or lesson the user names in `$ARGUMENTS`. If no topic is given, stop and ask for one.

## Contexts
Read these files before writing:
- `career-kb/profile.json` — the only source of facts (roles, projects, numbers). Never invent one; if the post needs a fact that isn't there, ask.
- `career-kb/general-standards.md` — branding
- `career-kb/communication-rules.md` — voice
- `career-kb/sound-like-human-standards.md` — must pass every rule in it
- `career-kb/social-media-standards.md` — the post rule set (structure, hooks, examples, discussion, images, tone)
- Ignore `career-kb/linkedin-standards.md` (profile only).

## Steps
1. Pick the one insight the post carries. One per post — if the topic holds several, ask which.
2. Draft along the formula from `social-media-standards.md` (*Post structure*), with a real story from `profile.json` behind the lesson.
3. Self-check against `social-media-standards.md` and `sound-like-human-standards.md` line by line; cut every sentence that adds nothing.
4. If an image would carry part of the message, describe it in one line below the post — don't decorate.
5. Write `career-kb/output/LinkedIn_Post_[slug]_[language].txt` for German and English, and return both paths plus the insight the post makes.
