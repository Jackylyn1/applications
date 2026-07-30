## Communication Rules for Authentic Applications

These govern the **voice** across **every** channel — CV, cover letter, LinkedIn profile and social media (not just applications). Sources: `Communication_Rules_for_Authentic_Applications.pdf`, `Professional_Branding_Standards.pdf` (Group A writing style), `LinkedIn_Profile_Standards.pdf` (its "Writing Style" and "Technical Communication" sections apply to every channel, so they live here, not in `linkedin-standards.md`).

**Read `sound-like-human-standards.md` together with this file — always, for every generated text** (Jacqueline, 2026-07-30). It holds the `Human_Writing_Ruleset.pdf` rules: the buzzword and stock-phrase blacklists, the hedging ban, rhythm and sentence-opening variation, and the editing checklist. This file governs *what* the voice says; that one governs *whether it reads as a human wrote it*.

### Core principle
- Write like an engineer, not like a marketer.
- Optimize for credibility rather than perfection.
- Sound thoughtful, calm and authentic instead of overly polished.

### Mindset to communicate
- Focus on understanding systems rather than collecting technologies.
- Show curiosity through questions, learning and improvement.
- Demonstrate enjoyment of solving complex problems.
- Highlight continuous improvement and evidence-based decision making.

### Preferred tone
- Professional but approachable — in German explicitly **professionell, aber locker** (Jacqueline, 2026-07-28): relaxed enough to read like a person, never stiff, never chummy. It should read pleasantly *and* let a recruiter orient in seconds; if a sentence serves only the reading experience, it goes.
- Confident without exaggeration.
- Honest about strengths and learning areas.
- Technical, precise and easy to understand.
- Curious rather than self-promotional.

### Writing style
- Concrete examples over abstract claims.
- Describe engineering decisions, not just technology lists.
- Explain trade-offs and reasoning **in the prose sections and in interviews — never inside a bullet point.** A bullet is too short to carry a "because"; forcing one in is what turns bullets into paragraphs (see *Bullet points*).
- Show measurable impact whenever possible. (What counts as impact → `general-standards.md`, *Name the outcome*.)
- Short, clear sentences over elaborate wording.
- **Use the established technical term instead of paraphrasing it** (Jacqueline, 2026-07-28). If a pattern has a name, name it: at-least-once delivery made idempotent, event-driven architecture, multi-tenancy/tenant isolation, walk-forward validation, row-level access control, JIT compilation. "Self-built distributed system" is a description where a term exists. Precision is what makes it read as engineering — but only ever for what the KB actually supports (see *Never invent* in `general-standards.md`).
- **In German texts, always carry the English technical term too** (Jacqueline, 2026-07-30). Where an established English term exists, it goes in — instead of the German word or right beside it: Multi-Tenancy (not only Mehrmandantenfähigkeit), Event-Driven Architecture, Domain-Driven Design, Real-Time Synchronisation, Test Automation, Row-Level Access Control, LLM Observability. Recruiters and ATS search the English term even on German-language profiles, so a German-only rendering is invisible to them. The German word alone is acceptable only where no established English term exists.
- **Say it the way she would say it out loud** (Jacqueline, 2026-07-30, on "Die Tiefe liegt bei Laravel, rund 4 Jahre 9 Monate davon in Produktion": *"Niemand schreibt das"*). Prose is first person and active, and experience is stated as a person states it: **"Laravel nutze ich seit ca. 5 Jahren in Produktion"**, not a nominal construction plus a month-exact figure. Round durations to "ca. X Jahre" in prose — the exact span belongs in the date ranges of the entries. Constructions to avoid: "Die Tiefe liegt bei …", "Mein Schwerpunkt liegt in …", "Zum Alltag gehören …", anything where the sentence has no subject who acts.
- **No narrator commentary.** Drop phrases that rate the content for the reader — "interesting is the structure", "technically exciting was", "worth mentioning". State the thing; the reader decides if it is interesting.

### Bullet points (hard)
Jacqueline, 2026-07-30. Governs **every bulleted list about work** — CV experience and projects, LinkedIn positions and projects. A recruiter scans bullets; they are an index, not a text.

- **`Topic: outcome` is the default shape.** Lead with the capability, discipline or component, then what it delivered — `Legacy Modernization: transforming critical systems in regulated environments into modern, scalable architectures`. The leading term is what the eye lands on and what recruiter search matches, so it goes first (which established term to pick → *Use the established technical term*).
- **One bullet per unit of work — never per fact** (Jacqueline, 2026-07-30, after a first pass split one position into ~16 thin bullets: "die Bulletpoints sind jetzt künstlich verknappt, dadurch sehr viele"). A unit of work is a project, a component or an initiative: the starter-kit optimisation, the external API, the test automation. Everything belonging to it — including its several outcomes — stays in **that one bullet**:
  - Right: `Website-Starterkit optimiert: Barrierefreiheit, DSGVO-Konformität, Ladezeiten 20 % schneller, SEO-Score von 60 auf 90`
  - Wrong: the same content as four bullets. Splitting is **artificial** — it inflates the list and destroys the information that these were one piece of work with several results.
- **Group by project, not by sentence.** Before writing, decide the units of work in the entry; each becomes one bullet. Two ideas belong in two bullets only when they are two *different* pieces of work — not because a sentence contains an "und".
- **Fewer, denser bullets beat many thin ones.** A position is roughly 4–8 bullets. If a list runs past ~10, the cause is almost always over-splitting, not an unusually rich role.
- **One to two lines each** (~200 characters). Longer than that means the bullet carries reasoning, which belongs in prose. Shorter than a full unit of work means it was split.
- **Solution-oriented, not duty-oriented.** Name the problem solved or the capability delivered, never the task assigned. "Responsible for the payment module" is a job description; "payment module: ..." with what it made possible is evidence. This is *Name the outcome* (`general-standards.md`) applied at bullet level — and it never licenses a stronger verb than the KB's (*Never upgrade the role she had*).
- **Numbers wherever `profile.json` has one** — throughput, runtime, page count, tenant count, coverage, duration. A real number outranks any adjective. Where no number exists, state the effect qualitatively and ask for it; never estimate (*Evidence over claims*).
  - **A count of something abstract needs an example beside it** (Jacqueline, 2026-07-30, editing "rund 10 Zielbegriffe" into "rund 10 Zielbegriffe mit lokalem Onlinemarketingbezug (z. B. Webseite Gelsenkirchen)": *"Beispielbegriffe ergänzt, um Vorstellung vom Scope zu geben"*). "10 Zielbegriffe", "14 Domains", "50 Ressourcen", "32 Kanäle" are unreadable on their own — the reader cannot tell whether the unit is big or trivial. Name one or two of the actual items in brackets and the number gets a scale. Concrete units (80 %, 5 Stunden, 227 Tests) already carry their own scale and need nothing added.
- **Cut filler.** Delete "responsible for", "involved in", "helped to", "worked on", "tasked with", "various", "several", "successfully", "state-of-the-art", "modern" as a standalone qualifier, and any "in order to". Drop the leading "I" and articles where the meaning survives.
  - **Honesty outranks this ban.** Where one of these weak verbs is the *accurate* one — "mitgearbeitet" / "worked on" for the Docker Compose dev/CI environment she did not build — the fix is to **drop the bullet**, never to swap in a stronger verb (`general-standards.md`, *Never upgrade the role she had*). A weak verb is a signal that the item does not carry its own bullet, not an invitation to upgrade it.
- **No terminal punctuation**, applied consistently across all bullets in a document.
- No narrator commentary and no negation inside bullets — the general rules apply here too, and a bullet has no room to recover from either.

### The person description stays prose (hard)
Jacqueline, 2026-07-30. The CV summary, the LinkedIn About section and the **cover-letter body** are **flowing text, never bullets** — they are the place that reads as a person rather than an index. All three carry the **same register**, and the LinkedIn About text (`output/LinkedIn_Profile_optimized_de.txt`, section 2) is the working model for it (Jacqueline, 2026-07-30: CV summary and cover letter in the same style as the About section).

- **Open with who she is, then what she does** — the structure she confirmed from a model text she supplied: role statement first ("Ich bin Softwareentwicklerin und baue …"), then the current responsibility with its components named, then how she works, then one concrete result.
  - *CV summary:* its first sentence is the mandated building span (`cv-standards.md`, *Summary framing*), which takes precedence over the role-statement opener; everything after that sentence follows this section.
  - *Cover letter:* the opener is the company's problem and her answer to it (`cover-letter-standards.md`, *Open strong*); from the second sentence on, this register applies.
- **On point, not detailed.** Answer only what a recruiter or HR employee needs to decide whether to read on: what she builds, where the depth is, the AI focus, the kind of problem she is good at. Project-level detail, tool inventories and chronology belong in the entries below, not here.
  - *CV summary and About only.* The cover letter has no entries below it, so it does carry one or two worked-out project examples (`cover-letter-standards.md`, *Default balance*) — what stays out there is the tool inventory and anything the posting does not ask for (`application-standards.md`, *Relevance filter*).
- **Every sentence earns its place.** No scene-setting opener, no closing sentence that summarises what was just said, no sentence that only serves the reading experience (*Preferred tone*).
- **A warm one-line closing invitation is allowed on LinkedIn** ("Wenn du jemanden für … suchst, schreib mich gern an"). The cover letter has its own close; the CV summary gets none.

### Never frame by negation (hard)
Jacqueline, 2026-07-28. Never state what she did **not** do, what does **not** exist, or what is missing — unless explicitly asked. A disclaimer draws the eye to exactly the thing it disclaims, and a reader who was never going to assume the bigger claim now thinks about it.
- No "not the overall architecture", no "no tests", no "not completed", no "only a small part".
- **Accuracy comes from what you list, not from what you rule out.** Naming the components she actually owned already scopes it correctly — the disclaimer adds nothing true and costs the sentence.
- No highlighting of gaps. Writing "2021–2024 and since 2025" spells out an employment gap that a plain date range would have carried silently; write the roles with their own dates and stop.
- Honesty questions (does she really have this skill, was she really responsible) are settled by *what is written*, never by *appending a limitation*. If something cannot be stated honestly without a disclaimer, leave it out instead.

### Fixed terminology
- **"Trading" is not used** as a label anywhere (Jacqueline, 2026-07-28) — not in project names, headings or descriptions. Describe what the system does technically (signal ingestion, parsing, order execution, risk gates, backtesting, quantitative research). The domain term inside a sentence where it is unavoidable is fine; the word as a *heading or identity* is not.
- **"MT 5"**, never "MetaTrader 5" or "MetaTrader5".

### Emphasize
Problem solving · architecture thinking · requirements engineering · optimization & performance · AI integration where relevant · learning through real projects · transferable engineering skills.

### Avoid
- Buzzwords, empty adjectives and marketing language.
- Generic claims and generic phrases.
- Exaggerated self-praise.
- Corporate and AI clichés (e.g. "passionate", "dynamic", "innovative", "results-driven").
- Claims without evidence.
- Artificial enthusiasm.
- **Sounding AI-generated.** Text that reads like ChatGPT wrote it discredits the content, however accurate it is: uniform sentence rhythm, three-item lists everywhere, "not only … but also", a closing sentence that summarises what was just said, adjectives doing the work evidence should do. The concrete blacklists (buzzwords, stock phrases, hedges, opening templates) and the editing checklist live in `sound-like-human-standards.md`.
- The "keep optimizing" idea **without its pragmatic qualifier**, and especially in German: "ich höre selten bei der ersten Lösung auf, die funktioniert" reads as overengineering, not as craft (Jacqueline, 2026-07-27). The English pattern *with* "if time allows it" is explicitly allowed — it is the unqualified version, and the German rendering in particular, that sends the opposite signal. In German either carry an equivalent constraint ("wenn es die Zeit zulässt") or show the behaviour through a result instead of claiming it.

### Authentic phrasing patterns (tone reference, not copy-paste)
- "I wanted to understand why it works, not only make it work."
- "I usually continue optimizing after the first working solution if time allows it." — the qualifier is load-bearing: it turns craft into judgement about time. Never drop it, and do not translate this one into German unqualified (see **Avoid**).
- "I enjoy learning unfamiliar technologies by understanding the underlying concepts."
- "I prefer making well-reasoned engineering decisions over following trends."
- AI work stated concretely, naming the engineering outcome rather than the model: "Built AI-assisted workflows for software development." · "Applied LLMs to improve development productivity and automate engineering tasks."

<!-- Cover-letter structure lives in cover-letter-standards.md; the "four questions every application answers" live in application-standards.md (kept out of this universal voice file to avoid duplication). -->

