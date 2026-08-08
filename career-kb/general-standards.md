# Universal Professional Branding Standards

The shared foundation for every channel — CV, cover letter, LinkedIn profile and social media. Hard rules; they override style preferences.

Where the other rules live (referenced, never duplicated here):
- Voice / tone / phrasing → `communication-rules.md`
- CV & cover-letter-only rules → `application-standards.md`
- Channel specifics → `linkedin-standards.md`, `social-media-standards.md`
- CV build/layout → `cv-standards.md`; cover-letter structure → `cover-letter-standards.md`

Sources: `Application_Standards_and_Career_Guidelines.pdf`, `Professional_Branding_Standards.pdf` (Group A), `LinkedIn_Profile_Standards.pdf` (positioning, evidence, philosophy and AI sections).

## Positioning (project this on every channel)
- Present [applicant] as an experienced software engineer with growing architectural expertise.
- Show an engineer who understands systems end-to-end and bridges business and technology.
- Show strategic thinking, not just implementation: architecture before implementation.
- Headline positioning: **"Software Engineer with Architecture and AI Focus."**
- Target roles: AI Software Developer, AI Consultant, Solution Architect, Software Architect. PHP Developer is a strong baseline.
- Core differentiator: she designs systems rather than merely implementing features — measurable optimization, architecture decisions, AI integration, performance engineering, continuous improvement.
- Never position her as backend-only. Backend is the deepest area, not the boundary. Python, TypeScript/frontend and containers/CI belong in the first visible lines of every channel, not in a technology list further down. "Backend-Software" as an opening self-description is wrong.

## AI positioning (every channel) — the primary focus
- AI is the main focus of the profile and has to be discoverable as such: in the first visible line of every channel, in role titles where it is genuinely true, and in the search terms she wants to be found under.
- AI is a focus, not a separate identity. Show it through engineering work, never as a buzzword. The fix for "too little AI" is more AI evidence, never more AI claims.
- What to show: she knows where AI creates measurable value, evaluates tools critically, optimises workflows with them, learns fast, and integrates AI into software engineering.
- Never reduce her AI work to a development tool. Formulations like "LLMs are a tool for me, not a topic of their own" undersell it. Make visible: agent workflows, subagents, MCP, deterministic verification of AI findings, prompt/context/token optimisation, model comparison with documented cost-vs-quality trade-offs, LLM observability/tracing.

## Evidence over claims (hard)
- Never claim a skill — demonstrate it through projects, achievements, metrics, architecture decisions, technical examples and lessons learned. Show, don't tell.
- Never invent. Use only facts from `profile.json`: no invented skills, tools, experience, dates, numbers or metrics, on any channel.
- If something is missing, propose a formulation and ask. Do not fill the gap.
- If a posting wants something absent from the KB, map it to a genuine adjacent skill — or, only if it is in the role's `must_learn`, present it honestly as "currently strengthening".

## Never upgrade the role she had (hard)
Overstatement rarely enters as an invented fact. It enters as a stronger word for a real one and survives review because the underlying activity is genuine.

- **Keep the KB's verb.** "Used" does not become "introduced", "worked on" does not become "built", "contributed to" does not become "designed", "supported" does not become "led". A verb that feels weak is information, not a formatting problem: ask her, never pick a synonym.
- **A competence may headline an entry only if that entry's own evidence carries it.** Architecture, consulting or performance engineering belongs in a job title, headline or top-billed skill only when the work named under that entry demonstrates it. Otherwise it stays where its evidence is: one component, one project, one volunteer role.
- **Name the component, not the discipline.** "Real-time pivot-event synchronisation" and "multi-tenant REST API" are hers. "Softwarearchitektur" as a summary of the same work claims the whole field. The component is more honest, more precise (`communication-rules.md`, *Use the established technical term*) and needs no disclaimer.
- **Extending an existing system is never building it.** Where the KB says a system was already there, the only honest verbs are "extended", "worked on", "added X to" — never "built", "designed" or "implemented the mechanism". Her own component inside it (the `laravel-pivot-events` package, the `PivotEvents` domain) may be claimed fully; the host system may not.
- **Use the plain role noun — no elevating prefix.** "Kern-", "Lead", "Senior", "Principal" and "Haupt-" are claims about rank. Plain "Entwicklerin" / "Software Engineer" is honest and stronger; the components named underneath do the ranking.
- **Team size stays out.** How many people were in the team says nothing about her contribution: a small number invites the wrong inference, a large one implies a share she did not have. `profile.json` keeps the real figure so no text can overstate it, but the default is to omit it and name her components. Team size she coordinated is her own scope of responsibility and may be stated (~15 at Narutorpg.de).
- **Drop scope adjectives in front of the product.** "Kassensystem", not "verteiltes Kassensystem". The distributed nature belongs in the bullet that shows it — cloud back-office, on-premise servers, mobile terminals.
- **Tools she used are not achievements she owns.** Naming a framework, pipeline or observability stack is fine. Implying she chose, built or introduced it is not, unless the KB says so.
- **Flag, do not soften silently.** When a claim has to be reduced, note what was reduced and why, and add the question that would restore the stronger version.

## Name the outcome, not just the activity (hard)
- Every achievement states what it changed, not only what she did. "Built X" is half a sentence; "built X, which did Y" is the whole one.
- Prefer measurable improvement over trends, and measurable business value over an activity list.
- This applies especially to changes she initiated rather than was assigned (AI-assisted development at Gastro IT, automated testing and the starter-kit optimisation at wpt-online): the effect is the evidence.
- Use a real number where `profile.json` has one. Where none exists, describe the effect qualitatively and ask for the number. Never estimate one (*Evidence over claims*).

## Engineering philosophy to communicate
- Systems thinking; optimisation mindset; evidence-based decisions; continuous improvement and iteration; architecture before implementation; business understanding; measuring outcomes.
- Automation is a through-line, not a claim: she automates what is repetitive and error-prone — test automation, CI pipelines, AI-assisted code audits, reproducible container environments, data pipelines. Show it through what she actually automated.

## Target impression (every channel)
- "This person is technically strong, analytical, trustworthy and understands software engineering beyond writing code."
- Explicitly not "someone chasing the latest trend". The move toward AI and architecture has to read as a natural next step.
