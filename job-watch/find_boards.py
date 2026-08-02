#!/usr/bin/env python3
"""find_boards — discover which ATS a company publishes through.

Every pattern below is a company's own public, documented, unauthenticated job
board endpoint, meant to be consumed by third parties (that is what powers their
careers pages and partner feeds). Probing them is not scraping.

Usage:
    python find_boards.py n26 celonis langfuse ...
    python find_boards.py --file companies.txt

Prints the config snippet for every board that resolves, ready to paste into
config.json under "boards".
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

UA = "job-watch/1.0 (personal job search; contact j.urban@gastroit.net)"

# name -> (url template, callable returning the number of postings found)
PATTERNS = {
    "greenhouse": (
        "https://boards-api.greenhouse.io/v1/boards/{s}/jobs",
        lambda d: len(d.get("jobs", [])),
    ),
    "ashby": (
        "https://api.ashbyhq.com/posting-api/job-board/{s}",
        lambda d: len(d.get("jobs", [])),
    ),
    "lever": (
        "https://api.lever.co/v0/postings/{s}?mode=json",
        lambda d: len(d) if isinstance(d, list) else 0,
    ),
    "workable": (
        "https://apply.workable.com/api/v1/widget/accounts/{s}",
        lambda d: len(d.get("jobs", [])),
    ),
    "recruitee": ("https://{s}.recruitee.com/api/offers/", lambda d: len(d.get("offers", []))),
    "smartrecruiters": (
        "https://api.smartrecruiters.com/v1/companies/{s}/postings",
        lambda d: d.get("totalFound", len(d.get("content", []))),
    ),
}


def probe(slug):
    """Return (ats, url, count) for the first pattern that resolves, else None."""
    for ats, (template, counter) in PATTERNS.items():
        url = template.format(s=slug)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
            )
            # Every PATTERNS template is a hardcoded https:// endpoint, so the
            # scheme cannot be influenced by the slug the user passes in.
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8", "replace"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            continue
        try:
            count = counter(data)
        except (AttributeError, TypeError):
            continue
        if count:
            return ats, url, count
    return None


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("slugs", nargs="*", help="company slugs to probe")
    ap.add_argument("--file", help="file with one slug per line")
    args = ap.parse_args()

    slugs = list(args.slugs)
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            slugs += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not slugs:
        ap.error("give at least one slug, or --file")

    found = []
    for slug in slugs:
        hit = probe(slug)
        if hit:
            ats, _url, count = hit
            print(f"  OK   {slug:24} {ats:16} {count:4} postings")
            found.append({"ats": ats, "slug": slug})
        else:
            print(f"  --   {slug:24} no public board found", file=sys.stderr)

    print(f"\n{len(found)}/{len(slugs)} resolved. Paste into config.json:\n")
    print('  "boards": ' + json.dumps(found, indent=2)[2:].replace("\n", "\n  "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
