"""Unit tests for the pure logic in career-kb/tools.

Scope is deliberately the parts a refactor can silently break: text hygiene,
patch merging and the CV content transforms. Everything that needs LibreOffice,
Chromium or a real DOCX template is left to render_application.py's own checks.
"""

import datetime
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / 'career-kb' / 'tools'
sys.path.insert(0, str(TOOLS))

import ats_hygiene
import build_cv
import build_letter
from apply_cv_patch import apply_patch

# ---------------------------------------------------------------- hygiene ----


def test_norm_text_replaces_dashes_and_entities():
    assert ats_hygiene.norm_text('a—b–c&mdash;d') == 'a-b-c-d'  # noqa: RUF001


def test_count_violations_counts_every_form():
    assert ats_hygiene.count_violations('—–&ndash;') == 3  # noqa: RUF001
    assert ats_hygiene.count_violations('plain - hyphen') == 0


def test_norm_file_rewrites_in_place(tmp_path):
    f = tmp_path / 'letter.html'
    f.write_text('<p>a—b</p>', encoding='utf-8')
    assert ats_hygiene.norm_file(str(f)) == 1
    assert f.read_text(encoding='utf-8') == '<p>a-b</p>'


# -------------------------------------------------------------- CV content ---


@pytest.mark.parametrize(
    ('right', 'expected'),
    [
        ('03.2025 - heute | Wuppertal', ('03.2025 - heute', 'Wuppertal')),
        ('2019 - 2021 | Essen | Remote', ('2019 - 2021', 'Essen · Remote')),
        ('seit Januar | Bochum', ('seit Januar', 'Bochum')),
        ('React, TypeScript', ('', 'React, TypeScript')),
        ('', ('', '')),
    ],
)
def test_split_timespan(right, expected):
    assert build_cv._split_timespan(right) == expected


def _sections():
    return [
        {
            'type': 'experience',
            'items': [
                {'title': 'New', 'bullets': ['n1', 'n2']},
                {'title': 'Old', 'bullets': ['o1', 'o2', 'o3']},
            ],
        }
    ]


def test_drop_bullets_takes_the_oldest_trailing_bullets_first():
    sections, dropped = build_cv._drop_bullets(_sections(), 2)
    assert [t for t, _ in dropped] == ['Old', 'Old']
    assert sections[0]['items'][1]['bullets'] == ['o1']
    assert sections[0]['items'][0]['bullets'] == ['n1', 'n2']


def test_drop_bullets_never_empties_an_entry():
    sections, dropped = build_cv._drop_bullets(_sections(), 99)
    assert all(it['bullets'] for it in sections[0]['items'])
    assert len(dropped) == 3


def test_drop_bullets_is_a_noop_for_zero():
    assert build_cv._drop_bullets(_sections(), 0)[1] == []


# ------------------------------------------------------------ letter dates ---


def test_format_date_uses_hardcoded_month_names():
    day = datetime.date(2026, 3, 9)
    assert build_letter.format_date('de', day) == 'Gelsenkirchen, 9. März 2026'
    assert build_letter.format_date('en', day) == 'Gelsenkirchen, 9 March 2026'


def test_build_letter_rejects_missing_fields():
    with pytest.raises(SystemExit):
        build_letter.build({'company': 'Acme'}, 'de')


LETTER_CONTENT = {
    'company': 'Acme',
    'tagline': 'Tagline',
    'subject': 'Subject',
    'salutation': 'Hallo Acme-Team,',
    'paragraphs': ['One paragraph.'],
}


# The real signature is untracked on purpose, so these tests supply their own
# instead of reading it - otherwise CI and a fresh clone would fail here.
@pytest.mark.parametrize('lang', ['de', 'en'])
def test_build_letter_embeds_the_signature(lang, tmp_path, monkeypatch):
    png = tmp_path / 'signature.png'
    png.write_bytes(b'\x89PNG\r\n\x1a\n')
    monkeypatch.setattr(build_letter, 'SIGNATURE', str(png))
    assert 'src="data:image/png;base64,' in build_letter.build(LETTER_CONTENT, lang)


def test_build_letter_asks_for_the_signature_when_it_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(build_letter, 'SIGNATURE', str(tmp_path / 'absent.png'))
    with pytest.raises(SystemExit, match='signature image not found'):
        build_letter.build(LETTER_CONTENT, 'de')


# --------------------------------------------------------------- CV patch ----

BASE = {
    'name': '[applicant]',
    'sections': [
        {'heading': 'PROFIL', 'type': 'summary', 'text': 'old summary'},
        {
            'heading': 'SKILLS',
            'type': 'skills',
            'lines': ['Backend: PHP', 'Frontend: React', 'KI: LLMs'],
        },
        {
            'heading': 'BERUFSERFAHRUNG',
            'type': 'experience',
            'items': [
                {'title': 'Web Dev', 'company': 'Gastro IT', 'bullets': ['a']},
                {'title': 'Support', 'company': 'wpt-online', 'bullets': ['b']},
            ],
        },
        {
            'heading': 'PROJEKTE',
            'type': 'experience',
            'items': [
                {'title': 'Signal Pipeline', 'bullets': ['p']},
                {'title': 'Backtesting Harness', 'bullets': ['q']},
            ],
        },
    ],
}


def section(doc, heading):
    return next(s for s in doc['sections'] if s['heading'] == heading)


def test_patch_leaves_the_base_untouched():
    apply_patch(BASE, {'summary': 'new'})
    assert section(BASE, 'PROFIL')['text'] == 'old summary'


def test_summary_is_replaced():
    doc, notes = apply_patch(BASE, {'summary': 'new summary'})
    assert section(doc, 'PROFIL')['text'] == 'new summary'
    assert notes == []


def test_skills_select_reorders_by_reference():
    doc, notes = apply_patch(BASE, {'skills': {'select': ['KI', 'Backend', 'Frontend']}})
    assert section(doc, 'SKILLS')['lines'][0] == 'KI: LLMs'
    assert notes == []


def test_dropping_a_skill_line_is_flagged():
    _, notes = apply_patch(BASE, {'skills': {'select': ['KI']}})
    assert len(notes) == 1 and 'skill line(s) dropped' in notes[0]


def test_dropping_a_job_is_flagged_but_dropping_a_project_is_not():
    _, job_notes = apply_patch(BASE, {'experience': {'select': ['Gastro IT']}})
    assert len(job_notes) == 1 and 'work-experience' in job_notes[0]
    # Projects are meant to be a curated subset, so trimming them is silent.
    _, project_notes = apply_patch(BASE, {'projects': {'select': ['Signal Pipeline']}})
    assert project_notes == []


def test_rewrite_targets_the_base_order_then_select_reorders():
    doc, _ = apply_patch(
        BASE,
        {
            'experience': {
                'rewrite': {'wpt-online': {'bullets': ['rewritten']}},
                'select': ['wpt-online', 'Gastro IT'],
            }
        },
    )
    items = section(doc, 'BERUFSERFAHRUNG')['items']
    assert items[0]['bullets'] == ['rewritten']
    assert items[1]['title'] == 'Web Dev'


def test_select_still_finds_a_category_that_rewrite_renamed():
    # The model writes both keys against the base it was shown, so a rewrite
    # that renames a skill category must not make its own select unresolvable.
    doc, _ = apply_patch(
        BASE,
        {
            'skills': {
                'rewrite': {'KI': 'AI & LLM: LLMs'},
                'select': ['KI', 'Backend', 'Frontend'],
            }
        },
    )
    assert section(doc, 'SKILLS')['lines'][0] == 'AI & LLM: LLMs'


def test_projects_addresses_the_second_experience_section():
    doc, _ = apply_patch(BASE, {'projects': {'rewrite': {'Signal Pipeline': {'bullets': ['x']}}}})
    assert section(doc, 'PROJEKTE')['items'][0]['bullets'] == ['x']
    assert section(doc, 'BERUFSERFAHRUNG')['items'][0]['bullets'] == ['a']


@pytest.mark.parametrize(
    'patch',
    [
        {'unknown_key': 1},
        {'summary': ''},
        {'skills': {'select': 'KI'}},
        {'skills': {'nope': []}},
        {'experience': {'select': ['Gastro IT', 0]}},  # same entry twice
        {'experience': {'select': ['nothing matches this']}},
        {'experience': {'rewrite': {'Gastro IT': {'unknown_field': 1}}}},
        {'experience': {'rewrite': {'Gastro IT': {'bullets': 'not a list'}}}},
        {'experience': ['not an object']},
    ],
)
def test_invalid_patches_fail_loudly(patch):
    with pytest.raises(SystemExit):
        apply_patch(BASE, patch)


def test_ambiguous_selector_fails_rather_than_guessing():
    base = {
        'sections': [
            {
                'heading': 'X',
                'type': 'experience',
                'items': [{'title': 'Developer A'}, {'title': 'Developer B'}],
            }
        ]
    }
    with pytest.raises(SystemExit):
        apply_patch(base, {'experience': {'select': ['Developer']}})


# ------------------------------------------------- template smoke test -------
# Exercises the section dispatch against the real template. Skipped where the
# template is absent (e.g. a checkout without the binary assets).

TEMPLATE = TOOLS.parent / 'templates' / 'CV_Template_Rezi_Dec2025.docx'

SMOKE = {
    'name': '[applicant]',
    'contact': [
        'Gelsenkirchen',
        'info@perfectseowebsite.de',
        '+49 152 13839296',
        'github.com/Jackylyn1',
    ],
    'sections': [
        {
            'heading': 'EXPERIENCE',
            'type': 'experience',
            'items': [
                {
                    'title': 'Web Dev',
                    'company': 'Gastro IT',
                    'right': '03.2025 - heute | Wuppertal',
                    'bullets': ['built things'],
                },
                {'title': 'Support', 'company': 'wpt-online', 'bullets': ['helped']},
            ],
        },
        {'heading': 'PROFILE', 'type': 'summary', 'text': 'Summary text.'},
        {'heading': 'SKILLS', 'type': 'skills', 'lines': ['Backend: PHP, Python']},
        {
            'heading': 'EDUCATION',
            'type': 'education',
            'items': [
                {'degree': 'Fachinformatikerin', 'detail': 'IHK'},
            ],
        },
    ],
}


@pytest.mark.skipif(not TEMPLATE.exists(), reason='CV template not available')
def test_build_renders_every_section_in_canonical_order():
    doc, dropped = build_cv.build(SMOKE, str(TEMPLATE))
    text = '\n'.join(p.text for p in doc.paragraphs)
    assert dropped == []
    assert text.index('PROFILE') < text.index('SKILLS') < text.index('EXPERIENCE')
    assert text.index('EXPERIENCE') < text.index('EDUCATION')
    assert '03.2025 - heute | Web Dev' in text
    assert 'Fachinformatikerin' in text


@pytest.mark.skipif(not TEMPLATE.exists(), reason='CV template not available')
def test_build_rejects_an_unknown_section_type():
    bad = {'name': 'X', 'contact': [], 'sections': [{'heading': 'H', 'type': 'nope'}]}
    with pytest.raises(SystemExit):
        build_cv.build(bad, str(TEMPLATE))
