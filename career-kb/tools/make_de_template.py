#!/usr/bin/env python3
"""make_de_template.py — Derive the German CV template from the (ATS-fixed)
English template by string-replacing ONLY text content.

Rules (per user): the German template must be *exactly the same* as the English
one; only the language of the prose changes to German and dates become MM.YYYY.
Therefore:
  * SECTION HEADERS ARE LEFT IN ENGLISH (PROFESSIONAL SUMMARY / SKILLS /
    EXPERIENCE / PROJECT / EDUCATION). The ATS keys on the literal labels
    EXPERIENCE/EDUCATION/SKILLS; translating them makes the ATS report them
    missing. They are structural keys, not prose.
  * Only the readable prose (summary, skills lines, bullets, titles, education)
    is translated, and it is translated FAITHFULLY from the English placeholder
    (no invented tech tokens like "PHPUnit"/"PHPDoc" — those tripped the ATS
    "flattened blob" check).
  * Dates -> MM.YYYY, ongoing -> "heute".

Why string replacement (not paragraph edits): build_cv.py captures prototype
paragraphs BY INDEX, so every paragraph/run must stay in place. Editing <w:t>
text keeps the structure identical. The placeholder text never ships (build_cv
overwrites all body text); this exists so the template file itself scans clean.

Run: python tools/make_de_template.py
"""
import os, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "templates", "CV_Template_Rezi_Dec2025.docx")
DST = os.path.join(HERE, "templates", "CV_Template_Rezi_DE_Dec2025.docx")

# Exact English source string -> German. Matches raw document.xml (entities such
# as &amp; / &lt; preserved). Section headers are deliberately absent -> kept EN.
REPS = {
    # --- name + contact (placeholder; never ships). Each field is its own run,
    # so replace them individually. "Seoul, South Korea" as a contact field is
    # replaced here; the experience-date "..., Seoul, South Korea" is handled by
    # its own longer key above (applied first via longest-first ordering). ---
    "Charles Bloomberg": "Max Mustermann",
    "Seoul, South Korea": "Musterstadt, Deutschland",
    "charlesbloomberg@gmail.com": "max.mustermann@example.de",
    "(621) 799-5548": "+49 000 0000000",
    "in/cbloomberg": "in/maxmustermann",
    # --- summary ---
    "Passion for building inspiring companies through industry-leading tech, design, and execution. An experienced early-stage global executive with an economics degree from the University of Wisconsin - Madison. Looking to join as a global startup consultant.":
        "Leidenschaft für den Aufbau inspirierender Unternehmen durch branchenführende Technik, Design und Umsetzung. Erfahrene Führungskraft der Frühphase mit einem wirtschaftswissenschaftlichen Abschluss der University of Wisconsin - Madison. Ich suche eine Position als globaler Startup-Berater.",
    # --- skills lines (comma-separated -> ATS-safe) ---
    "Leadership: Speaking, Fundraising, Product Development, Communication, Partnerships, International Marketing":
        "Führung: Präsentation, Fundraising, Produktentwicklung, Kommunikation, Partnerschaften, internationales Marketing",
    "Front End: HTML, CSS, Bootstrap, Webflow | Design: Photoshop, Illustrator, Sketch":
        "Frontend: HTML, CSS, Bootstrap, Webflow | Design: Photoshop, Illustrator, Sketch",
    "Fields of Interest: Early-Stage Fundraising, Global Entrepreneurship, Web Design, Growth":
        "Interessengebiete: Frühphasen-Fundraising, globales Unternehmertum, Webdesign, Wachstum",
    # --- experience 1 ---
    "CEO &amp; Founder": "Geschäftsführer &amp; Gründer",
    "August 2015-Present, Seoul, South Korea": "08.2015 - heute, Seoul, Südkorea",
    "Built Rezi - the most loved resume software in the world, trusted by over 4,124,000 users.":
        "Rezi aufgebaut - die weltweit beliebteste Bewerbungssoftware, der über 4.124.000 Nutzer vertrauen.",
    "Founded Rezi at the age of 22. At 23, successfully globalized into South Korea growing to be South Korea's leading English resume company, the most awarded global startup in South Korea, and securing over $650,000 in investment, grants, and awards.":
        "Rezi mit 22 Jahren gegründet. Mit 23 erfolgreich nach Südkorea expandiert und zum führenden Anbieter für englische Bewerbungen ausgebaut - das meistausgezeichnete globale Startup Südkoreas, mit über 650.000 $ an Investitionen, Fördermitteln und Auszeichnungen.",
    "Collaborated with the development team to engineer scalable partnership strategies such as redemption-code-based access which resulted in over 50,000 new users in 1 month with zero marketing dollars spent.":
        "Gemeinsam mit dem Entwicklungsteam skalierbare Partnerstrategien konzipiert, etwa den Zugang über Einlösecodes, was zu über 50.000 neuen Nutzern in einem Monat ohne Marketingbudget führte.",
    "Accountable for developing new business models as a response towards market conditions and opportunities which resulted in the development of 3 new core departments including e-learning, global recruiting, and data-vending.":
        "Verantwortlich für die Entwicklung neuer Geschäftsmodelle als Reaktion auf Marktbedingungen und Chancen, woraus drei neue Kernbereiche entstanden: E-Learning, globales Recruiting und Datenvertrieb.",
    "16 full time employees; 4,123,390 users; $650,000 total raised investment; $38,000,000 valuation.":
        "16 Vollzeitmitarbeitende; 4.123.390 Nutzer; 650.000 $ Gesamtinvestition; 38.000.000 $ Bewertung.",
    # --- experience 2 ---
    "Web Developer": "Webentwickler",
    "May 2015-November 2015, La Crosse, WI ": "05.2015 - 11.2015, La Crosse, WI ",
    "Executed website redesign of kaplancleantech.com using Expression Engine as a CMS while working with marketing and sales teams. Optimized 3 landing page variants using, HTML, A/B testing software and customer feedback to increase leads for sales teams.":
        "Relaunch der Website kaplancleantech.com mit Expression Engine als CMS in Zusammenarbeit mit Marketing- und Vertriebsteams. Drei Landingpage-Varianten mittels HTML, A/B-Testing und Kundenfeedback optimiert, um mehr Leads für den Vertrieb zu erzielen.",
    "Lead the developing SEO strategies monitoring campaigns using MOZ Analytics for a 500k budget. Maintained performance through site analysis, and new keyword research. Prepared analytics and ranking reports presented to management.":
        "Leitung der Entwicklung von SEO-Strategien und Überwachung der Kampagnen mit MOZ Analytics bei einem Budget von 500k. Performance durch Website-Analysen und neue Keyword-Recherche gesichert. Analyse- und Ranking-Berichte für das Management erstellt.",
    "Executed Google Analytics tracking campaigns to maximize the effectiveness of 5 email re-marketing initiatives deployed using Salesforce software. Used Salesforce Object Query Language, C, and Python to search for data for specific information.":
        "Google-Analytics-Kampagnen umgesetzt, um die Wirksamkeit von fünf E-Mail-Remarketing-Initiativen mit Salesforce zu maximieren. Salesforce Object Query Language, C und Python zur gezielten Datensuche eingesetzt.",
    # --- experience 3 ---
    "Marketing Analyst": "Marketing-Analyst",
    "November 2014-May 2015, La Crosse, WI ": "11.2014 - 05.2015, La Crosse, WI ",
    "Relied and implement Tableau dashboards to track 6 marketing key performance indicators. Used data to create reports circulated amongst leadership. Collaborated with marketing specialists to improve marketing strategies to maximize ROI such as introducing Facebook retargeting.":
        "Tableau-Dashboards implementiert, um sechs Marketing-Kennzahlen zu verfolgen. Daten für Berichte an die Führungsebene aufbereitet. Mit Marketing-Spezialisten zusammengearbeitet, um Strategien zur Maximierung des ROI zu verbessern, etwa durch Facebook-Retargeting.",
    "Used SurveyMonkey to collect over 100 customer feedbacks used to conduct analysis, identify market trends, and calculate NPS. Used customer feedback data and optimization software to present and suggest website improvements to management.":
        "Über 100 Kundenrückmeldungen mit SurveyMonkey erhoben, um Analysen durchzuführen, Markttrends zu erkennen und den NPS zu berechnen. Kundenfeedback und Optimierungssoftware genutzt, um dem Management Website-Verbesserungen vorzuschlagen.",
    "Managed mobile 2 PPC strategy efforts, using Google AdWords Editor and Marin, by teaching marketing specialists best practices.":
        "Mobile PPC-Strategien mit Google AdWords Editor und Marin verantwortet und Marketing-Spezialisten Best Practices vermittelt.",
    # --- experience 4 ---
    "Web Development Intern": "Praktikant Webentwicklung",
    "June 2012-September 2012, Madison, WI": "06.2012 - 09.2012, Madison, WI",
    "Integrated Analytics and marketing pixels to track behavior when introducing promos which brought in over $235k in sales.":
        "Analytics und Marketing-Pixel integriert, um das Verhalten bei der Einführung von Aktionen zu verfolgen, was über 235k $ Umsatz brachte.",
    # --- project ---
    "Early-Stage Startup Architect": "Startup-Architekt (Frühphase)",
    "Independent Startup Consultant": "Unabhängiger Startup-Berater",
    "Worked with 3 global founders to bring well-executed minimum viable products to market through no-code and \"ship-first\" methodologies.":
        "Mit drei internationalen Gründern zusammengearbeitet, um durchdachte Minimum Viable Products über No-Code- und \"Ship-First\"-Methoden auf den Markt zu bringen.",
    # --- education ---
    "Bachelor of Science in Economics with a Mathematics Emphasis":
        "Bachelor of Science in Volkswirtschaftslehre mit Schwerpunkt Mathematik",
    "University of Wisconsin - Madison  • Powers-Knapp Scholar •  2014":
        "University of Wisconsin - Madison  • Powers-Knapp-Stipendiat •  2014",
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
            print("   ", repr(m[:70]))


if __name__ == "__main__":
    main()
