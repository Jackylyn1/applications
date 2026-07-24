#!/usr/bin/env python3
"""make_de_template.py — Derive the German CV template from the (ATS-fixed)
English template by string-replacing only text content.

Why string replacement (not paragraph edits): build_cv.py captures prototype
paragraphs BY INDEX (p[0] name, p[1] contact, p[2] section, p[3] body, p[5]
title, p[6] compdate, p[7] bullet, p[12] empty, p[36] skill). Replacing text
inside <w:t> runs leaves every paragraph and run in place, so the DE template
stays "exactly the same structure" and build_cv works with either template.
The placeholder text never ships (build_cv overwrites all body text); this
translation exists so the template file itself reads/scans as German.

Run: python tools/make_de_template.py
"""
import os, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "templates", "CV_Template_Rezi_Dec2025.docx")
DST = os.path.join(HERE, "templates", "CV_Template_Rezi_DE_Dec2025.docx")

# Exact English source string -> German replacement. Strings match the raw
# document.xml (HTML entities preserved, e.g. &amp;). Applied longest-first so
# no key is a prefix of a still-unreplaced longer key.
REPS = {
    # --- name + contact (4 runs) ---
    "Charles Bloomberg": "Max Mustermann",
    "Seoul, South Korea": "Musterstadt, Deutschland",
    "charlesbloomberg@gmail.com": "max.mustermann@example.de",
    "(621) 799-5548": "+49 000 0000000",
    "in/cbloomberg": "in/maxmustermann",
    # --- section headings ---
    "PROFESSIONAL SUMMARY": "PROFIL",
    "SKILLS": "KENNTNISSE",
    "EXPERIENCE": "BERUFSERFAHRUNG",
    "PROJECT": "PROJEKTE",
    "EDUCATION": "AUSBILDUNG",
    # --- summary ---
    "Passion for building inspiring companies through industry-leading tech, design, and execution. An experienced early-stage global executive with an economics degree from the University of Wisconsin - Madison. Looking to join as a global startup consultant.":
        "Leidenschaft für den Aufbau moderner Software mit Fokus auf Architektur und angewandte KI. Erfahrene Entwicklerin mit Schwerpunkt auf sauberem, wartbarem Code und messbaren Ergebnissen. Auf der Suche nach einer Rolle mit Verantwortung für Architektur und technische Umsetzung.",
    # --- skills lines ---
    "Leadership: Speaking, Fundraising, Product Development, Communication, Partnerships, International Marketing":
        "Backend: PHP, Laravel, Symfony, REST-APIs, PostgreSQL, MySQL",
    "Front End: HTML, CSS, Bootstrap, Webflow | Design: Photoshop, Illustrator, Sketch":
        "Frontend: TypeScript, JavaScript, Vue.js, Alpine.js, Tailwind CSS, HTML5, CSS3",
    "Fields of Interest: Early-Stage Fundraising, Global Entrepreneurship, Web Design, Growth":
        "Schwerpunkte: Softwarearchitektur, KI-Integration, DevOps, Requirements Engineering",
    # --- experience 1: titles/company/date/bullets ---
    "CEO &amp; Founder": "Geschäftsführer &amp; Gründer",
    "Rezi": "Beispiel GmbH",
    "August 2015-Present, Seoul, South Korea": "08.2015 - heute, Musterstadt, Deutschland",
    "Built Rezi - the most loved resume software in the world, trusted by over 4,124,000 users.":
        "Aufbau und Weiterentwicklung einer modernen Webanwendung mit PHP/Laravel und TypeScript.",
    "Founded Rezi at the age of 22. At 23, successfully globalized into South Korea growing to be South Korea's leading English resume company, the most awarded global startup in South Korea, and securing over $650,000 in investment, grants, and awards.":
        "Konzeption der Softwarearchitektur eines Greenfield-Projekts; Backend, Frontend und Datenmodell von Grund auf gestaltet.",
    "Collaborated with the development team to engineer scalable partnership strategies such as redemption-code-based access which resulted in over 50,000 new users in 1 month with zero marketing dollars spent.":
        "Integration von KI-Werkzeugen in den täglichen Entwicklungs-Workflow für Code-Analyse und Automatisierung.",
    "Accountable for developing new business models as a response towards market conditions and opportunities which resulted in the development of 3 new core departments including e-learning, global recruiting, and data-vending.":
        "Aufbau und Pflege der CI/CD-Pipelines sowie Containerisierung der Anwendung mit Docker.",
    "16 full time employees; 4,123,390 users; $650,000 total raised investment; $38,000,000 valuation.":
        "Testautomatisierung mit PHPUnit und Codeception nach dem BDD-Ansatz.",
    # --- experience 2 ---
    "Web Developer": "Webentwickler",
    "May 2015-November 2015, La Crosse, WI ": "05.2015 - 11.2015, Musterstadt ",
    "Executed website redesign of kaplancleantech.com using Expression Engine as a CMS while working with marketing and sales teams. Optimized 3 landing page variants using, HTML, A/B testing software and customer feedback to increase leads for sales teams.":
        "Eigenständige Planung, Umsetzung und Wartung von Webanwendungen für verschiedene Kunden.",
    "Lead the developing SEO strategies monitoring campaigns using MOZ Analytics for a 500k budget. Maintained performance through site analysis, and new keyword research. Prepared analytics and ranking reports presented to management.":
        "Entwurf und Umsetzung von Backend- und Frontend-Funktionalitäten sowie der zugrunde liegenden Datenbanken.",
    "Executed Google Analytics tracking campaigns to maximize the effectiveness of 5 email re-marketing initiatives deployed using Salesforce software. Used Salesforce Object Query Language, C, and Python to search for data for specific information.":
        "Testautomatisierung mit PHPUnit und Dokumentation mit PHPDoc; direkte Kundenkommunikation.",
    # --- experience 3 ---
    "Marketing Analyst": "Webentwicklung / Koordination",
    "Kaplan": "Beispiel AG",
    "November 2014-May 2015, La Crosse, WI ": "11.2014 - 05.2015, Musterstadt ",
    "Relied and implement Tableau dashboards to track 6 marketing key performance indicators. Used data to create reports circulated amongst leadership. Collaborated with marketing specialists to improve marketing strategies to maximize ROI such as introducing Facebook retargeting.":
        "Weiterentwicklung einer historisch gewachsenen Codebasis in einem proprietären Framework.",
    "Used SurveyMonkey to collect over 100 customer feedbacks used to conduct analysis, identify market trends, and calculate NPS. Used customer feedback data and optimization software to present and suggest website improvements to management.":
        "Analyse komplexer Legacy-Abhängigkeiten und Dokumentation technischer Prozesse.",
    "Managed mobile 2 PPC strategy efforts, using Google AdWords Editor and Marin, by teaching marketing specialists best practices.":
        "Koordination eines zehnköpfigen Teams und Abstimmung technischer wie organisatorischer Aufgaben.",
    # --- experience 4 ---
    "Web Development Intern": "Praktikant Webentwicklung",
    "Wisconsin Public Television": "Beispiel e.V.",
    "June 2012-September 2012, Madison, WI": "06.2012 - 09.2012, Musterstadt",
    "Integrated Analytics and marketing pixels to track behavior when introducing promos which brought in over $235k in sales.":
        "Mitarbeit an der Konzeption und Umsetzung einer Website inklusive SEO-Maßnahmen.",
    # --- project ---
    "Early-Stage Startup Architect": "Open-Source-Projekt",
    "Independent Startup Consultant": "Persönliches Projekt",
    "Worked with 3 global founders to bring well-executed minimum viable products to market through no-code and \"ship-first\" methodologies.":
        "Veröffentlichung eines quelloffenen Laravel-Pakets; Fokus auf sauberes, testbares Design.",
    # --- education ---
    "Bachelor of Science in Economics with a Mathematics Emphasis":
        "Fachinformatikerin für Anwendungsentwicklung",
    "University of Wisconsin - Madison  • Powers-Knapp Scholar •  2014":
        "Beispiel-Bildungsträger, Musterstadt  •  08.2019 - 06.2021",
}


def main():
    zin = zipfile.ZipFile(SRC, "r")
    doc = zin.read("word/document.xml").decode("utf-8")
    misses = []
    for old in sorted(REPS, key=len, reverse=True):
        if old in doc:
            doc = doc.replace(old, REPS[old])
        else:
            misses.append(old)
    data = doc.encode("utf-8")
    with zipfile.ZipFile(DST, "w") as zout:
        for info in zin.infolist():
            payload = data if info.filename == "word/document.xml" else zin.read(info.filename)
            zout.writestr(info, payload)
    zin.close()
    print(f"wrote {DST}")
    if misses:
        print("WARNING: source strings not found (not replaced):")
        for m in misses:
            print("   ", repr(m[:60]))


if __name__ == "__main__":
    main()
