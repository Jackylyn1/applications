## Communication Rules for Authentic Applications

These govern the voice across every channel — CV, cover letter, LinkedIn profile and social media. Sources: `Communication_Rules_for_Authentic_Applications.pdf`, `Professional_Branding_Standards.pdf` (Group A writing style), `LinkedIn_Profile_Standards.pdf` ("Writing Style", "Technical Communication").

Read `sound-like-human-standards.md` together with this file, always, for every generated text.

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
- Professional but approachable; in German professionell, aber locker: relaxed enough to read like a person, never stiff, never chummy. Cut any sentence that serves only the reading experience.
- Confident without exaggeration.
- Honest about strengths and learning areas.
- Technical, precise and easy to understand.
- Curious rather than self-promotional.

### Writing style
- Concrete examples over abstract claims.
- Describe engineering decisions, not technology lists.
- Explain trade-offs and reasoning in prose and in interviews, never inside a bullet point.
- Show measurable impact whenever possible (what counts → `general-standards.md`, *Name the outcome*).
- Short, clear sentences over elaborate wording.
- **Use the established technical term instead of paraphrasing it.** If a pattern has a name, name it: at-least-once delivery made idempotent, event-driven architecture, multi-tenancy/tenant isolation, walk-forward validation, row-level access control, JIT compilation. "Self-built distributed system" is a description where a term exists. Only ever for what the KB supports (`general-standards.md`, *Evidence over claims*).
- **In German texts, carry the English technical term too.** It replaces the German word or stands beside it: Multi-Tenancy (not only Mehrmandantenfähigkeit), Event-Driven Architecture, Domain-Driven Design, Real-Time Synchronisation, Test Automation, Row-Level Access Control, LLM Observability. Recruiters and ATS search the English term even on German profiles, so use the German word alone only where no established English term exists.
- **Say it the way she would say it out loud.** Prose is first person and active, and experience is stated as a person states it: "Laravel nutze ich seit ca. 5 Jahren in Produktion", not a nominal construction with a month-exact figure. Round durations to "ca. X Jahre" in prose; the exact span belongs in the entry's date range. Avoid "Die Tiefe liegt bei …", "Mein Schwerpunkt liegt in …", "Zum Alltag gehören …", and anything without a subject who acts.
- **The other language mirrors the voice, not the words.** The German and the English version of a text are two writings of the same thing in the same register, not a translation of one another. A joke, an idiom or a set phrase gets its equivalent in the target language rather than a literal rendering, and either version stays English where that is what she would say ("Challenge accepted!"). Wording may differ between the two where the register demands it; facts, numbers and claims may not.
- **No narrator commentary.** Drop phrases that rate the content for the reader: "interesting is the structure", "technically exciting was", "worth mentioning". State the thing.

### Bullet points (hard)
Governs every bulleted list about work — CV experience and projects, LinkedIn positions and projects. A recruiter scans bullets; they are an index, not a text.

- **`Topic: outcome` is the default shape.** Lead with the capability, discipline or component, then what it delivered — `Legacy Modernization: transforming critical systems in regulated environments into modern, scalable architectures`. The leading term is what recruiter search matches (which term → *Use the established technical term*).
- **One bullet per unit of work, never per fact.** A unit of work is a project, a component or an initiative: the starter-kit optimisation, the external API, the test automation. Everything belonging to it, including its several outcomes, stays in that one bullet.
  - Right: `Website-Starterkit optimiert: Barrierefreiheit, DSGVO-Konformität, Ladezeiten 20 % schneller, SEO-Score von 60 auf 90`
  - Wrong: the same content as four bullets, which hides that this was one piece of work with several results.
- **Group by project, not by sentence.** Decide the units of work in the entry first; each becomes one bullet. Two ideas belong in two bullets only when they are two different pieces of work, not because a sentence contains an "und".
- **Fewer, denser bullets beat many thin ones.** A position is roughly 4–8 bullets. A list past ~10 means over-splitting.
- **One to two lines each** (~200 characters). Longer means it carries reasoning, which belongs in prose; shorter means the unit of work was split.
- **Solution-oriented, not duty-oriented.** Name the problem solved or the capability delivered, never the task assigned. "Responsible for the payment module" is a job description; "payment module: …" with what it made possible is evidence. This never licenses a stronger verb than the KB's (`general-standards.md`, *Never upgrade the role she had*).
- **Numbers wherever `profile.json` has one** — throughput, runtime, page count, tenant count, coverage, duration. A real number outranks any adjective. Where none exists, state the effect qualitatively and ask; never estimate.
  - **A count of something abstract needs an example beside it**, so the reader can judge the scale. Right: "rund 10 Zielbegriffe mit lokalem Onlinemarketingbezug (z. B. Webseite Gelsenkirchen)". Wrong: "10 Zielbegriffe", "14 Domains", "50 Ressourcen", "32 Kanäle". Concrete units (80 %, 5 Stunden, 227 Tests) already carry their scale.
- **Cut filler.** Delete "responsible for", "involved in", "helped to", "worked on", "tasked with", "various", "several", "successfully", "state-of-the-art", standalone "modern", and any "in order to". Drop the leading "I" and articles where the meaning survives.
  - **Honesty outranks this ban.** Where a weak verb is the accurate one — "worked on" for the Docker Compose dev/CI environment she did not build — drop the bullet, never swap in a stronger verb.
- **No terminal punctuation**, applied consistently across all bullets in a document.
- No narrator commentary and no negation inside bullets.

### The person description stays prose (hard)
The CV summary, the LinkedIn About section and the cover-letter body are flowing text, never bullets. All three carry the same register; the LinkedIn About text (`output/LinkedIn_Profile_optimized_de.txt`, section 2) is the working model.

- **Open with who she is, then what she does:** role statement first ("Ich bin Softwareentwicklerin und baue …"), then the current responsibility with its components named, then how she works, then one concrete result.
  - *CV summary:* the first sentence is the mandated building span (`cv-standards.md`, *Summary framing*), which takes precedence over the role-statement opener. Everything after it follows this section.
  - *Cover letter:* the opener is the company's problem and her answer to it (`cover-letter-standards.md`, *Open strong*). From the second sentence on, this register applies.
- **On point, not detailed.** Answer only what a recruiter needs to decide whether to read on: what she builds, where the depth is, the AI focus, the kind of problem she is good at. Project-level detail, tool inventories and chronology belong in the entries below.
  - *CV summary and About only.* The cover letter has no entries below it, so it carries one or two worked-out project examples (`cover-letter-standards.md`, *Default balance*). What stays out there is the tool inventory and anything the posting does not ask for (`application-standards.md`, *Relevance filter*).
- **Every sentence earns its place.** No scene-setting opener, no closing sentence that summarises what was just said, no sentence that only serves the reading experience.
- **A warm one-line closing invitation is allowed on LinkedIn** ("Wenn du jemanden für … suchst, schreib mich gern an"). The cover letter has its own close; the CV summary gets none.

### Never frame by negation (hard)
Never state what she did not do, what does not exist, or what is missing, unless explicitly asked. A disclaimer draws the eye to exactly the thing it disclaims.
- No "not the overall architecture", no "no tests", no "not completed", no "only a small part".
- **Accuracy comes from what you list, not from what you rule out.** Naming the components she owned already scopes it correctly.
- No highlighting of gaps. Wrong: "2021–2024 and since 2025". Write the roles with their own dates and stop.
- Honesty questions are settled by what is written, never by appending a limitation. What cannot be stated honestly without a disclaimer stays out.

### Grammatical gender (hard)
She is a woman. Every text about her uses the feminine form, in every channel and every language that marks gender: "Softwareentwicklerin", "Entwicklerin", "Werkstudentin", "Mentorin". Never the generic masculine ("Softwareentwickler") and never a neutralising construction ("Person mit Erfahrung in …"). This covers job titles, role nouns in prose and bullets. Gender-star or colon forms (`Entwickler:in`) belong to postings addressing an open group; quoting an advertised job title verbatim is correct, but she writes about herself in the plain feminine form.

### Emphasize
Problem solving · architecture thinking · requirements engineering · optimization & performance · AI integration where relevant · learning through real projects · transferable engineering skills.

### Avoid
- Buzzwords, empty adjectives and marketing language.
- Generic claims and generic phrases.
- Exaggerated self-praise.
- Corporate and AI clichés ("passionate", "dynamic", "innovative", "results-driven").
- Claims without evidence.
- Artificial enthusiasm.
- **Sounding AI-generated.** Uniform sentence rhythm, three-item lists everywhere, "not only … but also", a closing sentence that summarises what was just said, adjectives doing the work evidence should do. The blacklists and the editing checklist live in `sound-like-human-standards.md`.
- The "keep optimizing" idea without its pragmatic qualifier. Wrong: "ich höre selten bei der ersten Lösung auf, die funktioniert" — it reads as overengineering. The English pattern with "if time allows it" is allowed; in German carry an equivalent constraint ("wenn es die Zeit zulässt") or show the behaviour through a result.

### Authentic phrasing patterns (tone reference, not copy-paste)
- "I wanted to understand why it works, not only make it work."
- "I usually continue optimizing after the first working solution if time allows it." — the qualifier is load-bearing. Never drop it, and never translate this one into German unqualified (see **Avoid**).
- "I enjoy learning unfamiliar technologies by understanding the underlying concepts."
- "I prefer making well-reasoned engineering decisions over following trends."
- AI work stated concretely, naming the engineering outcome rather than the model: "Built AI-assisted workflows for software development." · "Applied LLMs to improve development productivity and automate engineering tasks."

<!-- Cover-letter structure lives in cover-letter-standards.md; the "four questions every application answers" live in application-standards.md. -->
