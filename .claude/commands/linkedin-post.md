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
1. Start from what actually happened. Pick the one thing the post carries — an insight, an observation, a joke. If the topic holds several, ask which.
2. Draft it in her voice. `social-media-standards.md` (*Post structure*) offers a shape; it is optional, and a manufactured lesson is worse than none. Facts and numbers come from `profile.json`, and only where the story needs them.
3. Self-check against `social-media-standards.md` and `sound-like-human-standards.md`; cut every sentence that adds nothing — except a joke or a concrete detail, which are not filler.
4. If the user supplied an image, leave it alone and let it carry its part. If one would help, describe it in one line below the post — don't decorate.
5. Write `career-kb/output/LinkedIn_Post_[slug]_[language].txt` for German and English, and return both paths plus the insight the post makes.
