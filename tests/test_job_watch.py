"""Unit tests for job-watch's pure logic: text extraction, dedupe keys, parsing.

Nothing here touches the network, the SQLite state or the notification fan-out.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'job-watch'))

import watch

# ---------------------------------------------------------------- slugify ----


# NOTE: the ae/oe/ue expansion in slugify() never fires - NFKD has already split
# the umlaut into "u" + combining diaeresis by then, so "Müller" becomes
# "Muller", not "Mueller". These cases pin the CURRENT behaviour: changing it
# would change every alias key and re-notify cross-posted German offers once.
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Müller & Söhne GmbH', 'Muller-Sohne-GmbH'),
        ('Straße 1', 'Strasse-1'),
        ('  ---  ', 'unknown'),
        ('', 'unknown'),
        (None, 'unknown'),
    ],
)
def test_slugify(text, expected):
    assert watch.slugify(text) == expected


def test_slugify_respects_the_limit():
    assert watch.slugify('a' * 100, 10) == 'a' * 10


# ------------------------------------------------------------ html_to_text ---


def test_html_to_text_keeps_words_and_structure():
    html = (
        '<div><script>evil()</script><p>Erste Zeile</p>'
        '<ul><li>Punkt A</li><li>Punkt B</li></ul>'
        '<p>Zweite&nbsp;Zeile<br>umgebrochen</p></div>'
    )
    assert watch.html_to_text(html) == (
        'Erste Zeile\n\n- Punkt A\n- Punkt B\n\nZweite Zeile\numgebrochen'
    )


def test_html_to_text_unescapes_entities():
    assert watch.html_to_text('<p>Kaffee &amp; Kuchen</p>') == 'Kaffee & Kuchen'


def test_html_to_text_handles_empty_input():
    assert watch.html_to_text(None) == ''


def test_unwrap_hard_breaks_only_joins_mid_sentence():
    assert watch.unwrap_hard_breaks('wir suchen\neine Person') == 'wir suchen eine Person'
    assert watch.unwrap_hard_breaks('Ende.\nNeuer Satz') == 'Ende.\nNeuer Satz'


# -------------------------------------------------------------- dedupe -------


def test_normalize_url_strips_only_tracking_params():
    url = 'https://x.de/job/1/?jk=abc&utm_source=mail&refId=9'
    assert watch.normalize_url(url) == 'https://x.de/job/1?jk=abc'


def test_normalize_url_is_order_independent():
    assert watch.normalize_url('https://x.de/j?b=2&a=1') == watch.normalize_url(
        'https://x.de/j?a=1&b=2'
    )


def test_dedupe_key_falls_back_to_source_company_title_without_a_url():
    rec = {'source': 'stepstone', 'company': 'Acme GmbH', 'title': 'PHP Dev', 'url': ''}
    assert watch.dedupe_key(rec) == 'stepstone|Acme-GmbH|PHP-Dev'


def test_alias_key_is_board_independent():
    a = {'source': 'linkedin', 'company': 'Acme', 'title': 'PHP Dev'}
    b = {'source': 'indeed', 'company': 'Acme', 'title': 'PHP Dev'}
    assert watch.alias_key(a) == watch.alias_key(b)


# ---------------------------------------------------------------- jobspy -----


def test_cell_maps_pandas_nan_to_none():
    row = {'title': 'Dev', 'company': float('nan'), 'salary': None}
    assert watch.cell(row, 'title') == 'Dev'
    assert watch.cell(row, 'company') is None
    assert watch.cell(row, 'salary') is None


# ------------------------------------------------------------- stepstone -----


def test_stepstone_search_url_prefers_the_configured_url():
    assert watch.stepstone_search_url({'stepstone_url': 'https://x'}) == 'https://x'


def test_stepstone_search_url_is_built_from_term_and_location():
    url = watch.stepstone_search_url({'term': 'PHP Entwickler', 'location': 'Essen, NRW'})
    assert url.startswith('https://www.stepstone.de/jobs/php-entwickler/in-essen?')


def test_stepstone_detail_links_are_absolute_and_deduped():
    page = (
        '<a href="/stellenangebote--a-1?utm=x">A</a>'
        '<a href="/stellenangebote--a-1">A again</a>'
        '<a href="/stellenangebote--b-2">B</a>'
    )
    assert watch.stepstone_detail_links(page) == [
        'https://www.stepstone.de/stellenangebote--a-1',
        'https://www.stepstone.de/stellenangebote--b-2',
    ]


def test_job_posting_ld_finds_the_posting_inside_a_graph():
    page = (
        '<script type="application/ld+json">{"@type":"WebSite"}</script>'
        '<script type="application/ld+json">not json</script>'
        '<script type="application/ld+json">'
        '{"@graph":[{"@type":"Breadcrumb"},{"@type":"JobPosting","title":"Dev"}]}'
        '</script>'
    )
    assert watch.job_posting_ld(page)['title'] == 'Dev'


def test_job_posting_ld_returns_none_when_absent():
    assert watch.job_posting_ld('<html>nothing</html>') is None


def test_posting_to_record_flattens_the_schema_org_shape():
    posting = {
        'title': 'PHP Dev',
        'hiringOrganization': {'name': 'Acme'},
        'jobLocation': [{'address': {'addressLocality': 'Essen'}}],
        'datePosted': '2026-08-01T10:00:00Z',
        'employmentType': 'FULL_TIME',
        'description': '<p>Text &amp; mehr</p>',
    }
    rec = watch.posting_to_record(posting, 'https://fallback', {'term': 'php'})
    assert rec['company'] == 'Acme'
    assert rec['location'] == 'Essen'
    assert rec['date_posted'] == '2026-08-01'
    assert rec['url'] == 'https://fallback'
    assert rec['description'] == 'Text & mehr'


def test_posting_to_record_survives_a_missing_location():
    rec = watch.posting_to_record({}, 'https://x', {'term': 'php', 'location': 'Essen'})
    assert rec['location'] == 'Essen'
    assert rec['title'] == ''


# ------------------------------------------------------------ safety net -----


def test_fetch_refuses_non_http_urls():
    with pytest.raises(ValueError, match='non-HTTP'):
        watch.fetch('file:///etc/passwd')


def test_expand_env_substitutes_and_skips_unset(monkeypatch):
    monkeypatch.setenv('WATCH_TOKEN', 'abc')
    assert watch.expand_env('tgram://${WATCH_TOKEN}/1') == 'tgram://abc/1'
    monkeypatch.delenv('WATCH_TOKEN')
    assert watch.expand_env('tgram://${WATCH_TOKEN}/1') is None
