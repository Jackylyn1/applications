#!/usr/bin/env python3
"""apply_timespan_layout.py — Move each experience entry's timespan to the FRONT
of its title line in a template's placeholder, and turn the old right-tabbed
"Company <tab> Date, Location" line into a plain left-aligned "Company · Location".

Why: the raw templates put the date behind a right tab whose stop sat off-page
(20000 twips), so the timespan was invisible when the template was scanned.
This makes the placeholder match build_cv's generated layout (timespan leads the
title). Language-agnostic and idempotent (skips lines with no run-level tab).

Usage: python tools/apply_timespan_layout.py <template.docx> [<template2.docx> ...]
"""

import sys

from docx import Document
from docx.oxml.ns import qn

W_R, W_T, W_TAB = qn('w:r'), qn('w:t'), qn('w:tab')


def _split_date_location(text):
    """ "Date, Location" -> (date, location); a bare date yields an empty location."""
    if ',' in text:
        date, location = (s.strip() for s in text.split(',', 1))
        return date, location
    return text, ''


def _prepend_timespan(title_para, date):
    """Put "<date> | " in front of the title, unless it is already there."""
    ts = title_para._p.findall('.//' + W_T)
    if date and ts and ' | ' not in (ts[0].text or ''):
        ts[0].text = f"{date} | " + (ts[0].text or '')


def _rewrite_company_line(el, tab_runs, title_para):
    """Rewrite one tabbed "Company <tab> Date, Location" paragraph in place.

    Returns True if the paragraph was a company/date line and got rewritten.
    """
    ts = el.findall('.//' + W_T)
    if len(ts) < 2:
        return False
    company = (ts[0].text or '').strip()
    date, location = _split_date_location((ts[-1].text or '').strip())
    if title_para is not None:
        _prepend_timespan(title_para, date)
    # Drop the run-level tab; rewrite the line as "Company · Location".
    for r in tab_runs:
        for tab in r.findall(W_TAB):
            r.remove(tab)
    ts[0].text = company
    ts[-1].text = (' · ' + location) if location else ''
    return True


def transform(path):
    doc = Document(path)
    paras = doc.paragraphs
    changed = 0
    for i, p in enumerate(paras):
        el = p._p
        tab_runs = [r for r in el.findall(W_R) if r.find(W_TAB) is not None]
        if not tab_runs:
            continue  # not a tabbed company/date line
        changed += _rewrite_company_line(el, tab_runs, paras[i - 1] if i else None)
    doc.save(path)
    print(f"{path}: rewrote {changed} experience line(s)")


if __name__ == '__main__':
    for path in sys.argv[1:]:
        transform(path)
