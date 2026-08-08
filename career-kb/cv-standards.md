## CV Standards

CV-specific rules only. Universal branding → `general-standards.md`; voice → `communication-rules.md`; application-wide rules → `application-standards.md`.

### Layout (hard)
- Always build the CV from the stored template. Never generate or design a custom layout. This covers base templates and job-offer CVs alike.
- English CVs → `templates/CV_Template_Rezi_Dec2025.docx`.
- German CVs → `templates/CV_Template_Rezi_DE_Dec2025.docx` (structurally identical; German headings, German placeholders, `MM.YYYY` dates). Regenerate it with `tools/make_de_template.py` when the English template changes.
- Keep name and contact left-aligned (name = first extracted line) and use no em/en dashes.
- Optimize content, never layout.

### Content per application
- Use the existing CV as the master document.
- Customize summary, skills, projects and keywords for every application.
- Rewrite, reorder, drop or surface experience bullets per role when it helps. The standard bullets are a default, not fixed text. When a posting emphasizes something else — requirements engineering, database design, project leadership, online marketing/SEO — lead with the relevant experience, drawing on `profile.json` → `references` (the wpt-online Arbeitszeugnis). Leave the bullets as they are when the defaults already fit.

### Summary framing (hard — "Variant A", always)
- Open the summary with the full building span, not the first professional role. [applicant] has built software for 15+ years: first voluntarily in open-source and community projects (Narutorpg.de since 2009, Tierheim web work from ~2005), professionally since 2019.
- Right: "I have been building software for over 15 years, first through volunteer open-source and community projects and professionally since 2019, …"
- Wrong: "since 2019 I build/maintain web applications" — it undersells and misleads.
- This rule owns the first sentence only. The rest of the summary follows `communication-rules.md`, *The person description stays prose*, and the span sentence itself is first person and active.

### Bullets
- Experience and project bullets are the LinkedIn bullets: one bullet per unit of work, `Topic: outcome`, defined in `communication-rules.md`, *Bullet points*. What goes into a bullet → `application-standards.md`, *Project Description Standard*.
- CV and LinkedIn entries carry the same bullets, selected and reordered per role.

### Structure (hard)
- **Projects:** every project entry has a timespan, like experience. AI Engineering Experiments = 2024–heute; Execution Research & Backtesting Platform = 2025–2026; Laravel Pivot Events = 2025–heute. Put it in the item's `right` as `Timespan  |  <tech>` (tech optional).
- **Skills:** bulleted, with a bold category label (`KI & LLM-Engineering:`), same bullet marker and spacing as every other section. The item list stays normal. No custom spacers between skill lines.
- **Dates:** German CVs use `MM.YYYY` (`03.2025 - heute`, `08.2019 - 06.2021`), ongoing = `heute`. English CVs use `Mon YYYY` (`Mar 2025 - Present`). Year-only ranges (`2013 - 2017`) are fine where no month applies. The separator is a plain hyphen ` - `, never `—` or `–`.
- **Section order:** Profile/Summary, Skills, Experience, Projects, Education. Skills sits directly under the profile.
- **Experience layout:** each entry leads with its timespan on the title line — `Timespan | Job Title` (EN `Mar 2025 - Present | …`, DE `03.2025 - heute | …`) — with `Company · Location` left-aligned below. No right-aligned date tab. Projects carry no timespan prefix.

### Page length (hard)
- A second page is allowed only if it carries at least 10 lines of text.
- Below that, compact onto one page, least-destructive first:
  1. Tighten paragraph spacing (no content lost, font size unchanged).
  2. Only if that is not enough, drop the least important bullets — trailing bullets of the older or lower-listed roles first. Every role keeps at least one bullet, and log what was dropped.
- Shorten the wording inside the longest bullets before dropping any. A bullet carries a whole unit of work, so dropping one drops a whole project.
- Caps: never tighten below 0.82 spacing and never drop more than 3 bullets.
- If one page is still out of reach, keep the intact 2-pager and flag that page 2 is below target.
- Automated by `tools/build_fit.py`.
