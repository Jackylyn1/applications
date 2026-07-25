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


def transform(path):
    doc = Document(path)
    paras = doc.paragraphs
    changed = 0
    for i, p in enumerate(paras):
        el = p._p
        tab_runs = [r for r in el.findall(W_R) if r.find(W_TAB) is not None]
        if not tab_runs:
            continue                      # not a tabbed company/date line
        ts = el.findall('.//' + W_T)
        if len(ts) < 2:
            continue
        company = (ts[0].text or '').strip()
        datebloc = (ts[-1].text or '').strip()      # "Date, Location"
        if ',' in datebloc:
            date, location = (s.strip() for s in datebloc.split(',', 1))
        else:
            date, location = datebloc, ''
        # Prepend the timespan to the preceding (title) paragraph.
        if i >= 1 and date:
            tts = paras[i - 1]._p.findall('.//' + W_T)
            if tts and ' | ' not in (tts[0].text or ''):
                tts[0].text = f"{date} | " + (tts[0].text or '')
        # Drop the run-level tab; rewrite line as "Company · Location".
        for r in tab_runs:
            for tab in r.findall(W_TAB):
                r.remove(tab)
        ts[0].text = company
        ts[-1].text = (' · ' + location) if location else ''
        changed += 1
    doc.save(path)
    print(f"{path}: rewrote {changed} experience line(s)")


if __name__ == '__main__':
    for path in sys.argv[1:]:
        transform(path)
