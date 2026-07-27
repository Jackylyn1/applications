#!/usr/bin/env python3
"""job-watch — poll LinkedIn / Indeed / StepStone & co. for new offers, keep the
posting text verbatim, notify once per offer.

Every new offer is written to job-watch/inbox/ as a markdown file whose body is
the UNMODIFIED posting text, so oddities like "everybody has to bring their cat
to work - very important" survive into /generate-application.

Usage:
    python watch.py                     # poll all enabled sources, notify, remember
    python watch.py --dry-run           # poll + report, write nothing, notify nobody
    python watch.py --source stepstone  # restrict to one source (repeatable)
    python watch.py --recent 10         # list the last N offers already collected

Sources, queries and notification channels are configured in config.json.
Each new offer becomes inbox/<date>_<source>_<company>_<title>_<hash>.md: YAML
front matter (company, title, location, url, date_posted, salary, remote,
job_type, query, first_seen) followed by the posting text exactly as published.
Feed that file to /generate-application.
"""

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
INBOX = os.path.join(HERE, "inbox")
STATE = os.path.join(HERE, "state.db")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


# ---------------------------------------------------------------- helpers

def slugify(text, limit=60):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text[:limit] or "unknown"


def html_to_text(raw):
    """HTML -> plain text, preserving paragraphs and bullets.

    Deliberately conservative: we drop markup, never words. The posting text is
    the product here, so nothing gets summarised or trimmed.
    """
    if not raw:
        return ""
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|section|h[1-6]|tr|table|ul|ol)>", "\n\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "\n- ", t)
    t = re.sub(r"(?i)</li>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = t.replace("\xa0", " ").replace("\r", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def unwrap_hard_breaks(text):
    """Join lines a source hard-wrapped mid-sentence (Arbeitsagentur style)."""
    return re.sub(r"(?<=[a-zäöüß,])\n(?=[a-zäöüß])", " ", text)


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def expand_env(value):
    """Replace ${VAR} in config strings so tokens live in the environment.

    Returns None if the URL references a variable that is not set, so a
    half-filled channel is skipped instead of failing at send time.
    """
    missing = [v for v in re.findall(r"\$\{(\w+)\}", value) if not os.environ.get(v)]
    if missing:
        print(f"(skipping notify channel — unset: {', '.join(missing)})", file=sys.stderr)
        return None
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ[m.group(1)], value)


# ---------------------------------------------------------------- state

def open_state():
    con = sqlite3.connect(STATE)
    con.execute("""CREATE TABLE IF NOT EXISTS seen (
        key TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT,
        url TEXT, first_seen TEXT, path TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS alias (
        akey TEXT PRIMARY KEY, key TEXT)""")
    con.commit()
    return con


# Params that identify a session/campaign rather than the posting. Everything
# else is kept — Indeed's job id lives in ?jk=, so blanket-stripping the query
# string would collapse every Indeed hit onto one key.
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "refId", "trackingId", "trk", "trkInfo", "position", "pageNum", "eBP",
    "refresh", "originalSubdomain", "src", "sid", "cd", "from", "gclid",
    "sort", "action",
}


def normalize_url(url):
    if not url:
        return ""
    parts = urllib.parse.urlsplit(url)
    query = sorted((k, v) for k, v in
                   urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
                   if k not in TRACKING_PARAMS)
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path.rstrip("/"),
         urllib.parse.urlencode(query), ""))


def dedupe_key(rec):
    """Exact identity of one posting on one board."""
    url = normalize_url(rec.get("url"))
    if url:
        return url
    return f"{rec['source']}|{slugify(rec.get('company'))}|{slugify(rec.get('title'))}"


def alias_key(rec):
    """Board-independent identity, so a job cross-posted to LinkedIn, Indeed and
    StepStone notifies once instead of three times."""
    return f"{slugify(rec.get('company'), 40)}|{slugify(rec.get('title'), 60)}"


# ---------------------------------------------------------------- sources

def from_jobspy(query, sites, cfg):
    """LinkedIn / Indeed / Glassdoor / Google via the JobSpy scraper library."""
    from jobspy import scrape_jobs

    out = []
    for site in sites:
        kwargs = dict(
            site_name=[site],
            search_term=query["term"],
            location=query.get("location", ""),
            results_wanted=query.get("results", 20),
            hours_old=query.get("hours_old", 48),
            country_indeed=query.get("country", "Germany"),
            description_format="markdown",
            verbose=0,
        )
        if site == "linkedin":
            # one extra request per hit, but without it LinkedIn gives no body
            kwargs["linkedin_fetch_description"] = cfg.get("linkedin_fetch_description", True)
        if site == "google":
            kwargs["google_search_term"] = (
                f"{query['term']} jobs in {query.get('location','')}".strip())
        try:
            df = scrape_jobs(**kwargs)
        except Exception as exc:  # one flaky board must not sink the run
            print(f"  ! {site}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        for _, row in df.iterrows():
            get = lambda k: (None if row.get(k) is None or str(row.get(k)) == "nan"
                             else row.get(k))
            body = get("description") or ""
            out.append({
                "source": site,
                "title": get("title") or "",
                "company": get("company") or "",
                "location": get("location") or query.get("location", ""),
                "url": get("job_url") or get("job_url_direct") or "",
                "date_posted": str(get("date_posted") or ""),
                "job_type": get("job_type") or "",
                "remote": bool(get("is_remote")),
                "salary": " - ".join(str(x) for x in (get("min_amount"), get("max_amount")) if x),
                "description": body,
                "query": query["term"],
            })
        print(f"  {site}: {len(df)} hits")
    return out


def from_stepstone(query, cfg):
    """StepStone has no API. The search page is plain HTML and every detail page
    carries a schema.org JobPosting with the complete description."""
    url = query.get("stepstone_url")
    if not url:
        loc = slugify(query.get("location", "").split(",")[0]).lower()
        url = (f"https://www.stepstone.de/jobs/{slugify(query['term']).lower()}"
               f"/in-{loc}?radius={query.get('radius', 30)}&sort=2")
    try:
        page = fetch(url)
    except Exception as exc:
        print(f"  ! stepstone search: {type(exc).__name__}: {exc}", file=sys.stderr)
        return []

    links, seen = [], set()
    for href in re.findall(r'href="(/stellenangebote--[^"#]+)"', page):
        clean = href.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            links.append(urllib.parse.urljoin("https://www.stepstone.de", clean))

    cap = query.get("results", 20)
    out = []
    for i, link in enumerate(links[:cap]):
        if i:
            time.sleep(cfg.get("stepstone_delay", 1.5))  # be a polite guest
        try:
            detail = fetch(link)
        except Exception as exc:
            print(f"  ! stepstone detail: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        posting = None
        for block in re.findall(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', detail, re.S):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
            for node in nodes if isinstance(nodes, list) else [nodes]:
                if isinstance(node, dict) and node.get("@type") == "JobPosting":
                    posting = node
                    break
            if posting:
                break
        if not posting:
            continue
        loc = posting.get("jobLocation") or {}
        loc = loc[0] if isinstance(loc, list) and loc else loc
        addr = (loc or {}).get("address", {}) if isinstance(loc, dict) else {}
        out.append({
            "source": "stepstone",
            "title": posting.get("title") or "",
            "company": (posting.get("hiringOrganization") or {}).get("name") or "",
            "location": addr.get("addressLocality") or query.get("location", ""),
            "url": posting.get("url") or link,
            "date_posted": (posting.get("datePosted") or "")[:10],
            "job_type": posting.get("employmentType") or "",
            "remote": False,
            "salary": "",
            "description": html_to_text(posting.get("description")),
            "query": query["term"],
        })
    print(f"  stepstone: {len(out)} hits")
    return out


# ---------------------------------------------------------------- output

def write_offer(rec, key):
    os.makedirs(INBOX, exist_ok=True)
    stamp = dt.date.today().isoformat()
    # the key hash keeps two same-titled postings (same employer, other city)
    # from overwriting each other
    tag = hashlib.sha1(key.encode()).hexdigest()[:6]
    name = (f"{stamp}_{rec['source']}_{slugify(rec['company'], 30)}"
            f"_{slugify(rec['title'], 40)}_{tag}.md")
    path = os.path.join(INBOX, name)
    meta = {k: rec.get(k, "") for k in
            ("source", "company", "title", "location", "url", "date_posted",
             "job_type", "remote", "salary", "query")}
    meta["first_seen"] = dt.datetime.now().isoformat(timespec="seconds")
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items())
    body = unwrap_hard_breaks(rec.get("description") or "")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"---\n{front}\n---\n\n# {rec['title']} — {rec['company']}\n\n{body}\n")
    return path


def notify(records, cfg, dry_run):
    urls = [expand_env(u) for u in cfg.get("notify", []) if not u.startswith("#")]
    urls = [u for u in urls if u]
    lines = [f"- {r['title']} @ {r['company']} ({r['location'] or '?'}) [{r['source']}]\n  {r['url']}"
             for r in records]
    body = "\n".join(lines)
    title = f"{len(records)} new job offer(s)"

    print(f"\n{title}\n{body}\n")
    if dry_run or not urls:
        if not urls and not dry_run:
            print("(no notify channels configured — inbox files written only)")
        return
    try:
        import apprise
    except ImportError:
        print("(apprise not installed — skipping push notifications)", file=sys.stderr)
        return
    ap = apprise.Apprise()
    for u in urls:
        ap.add(u)
    ap.notify(title=title, body=body)


def list_recent(limit):
    con = open_state()
    rows = con.execute("SELECT first_seen, source, company, title, url FROM seen "
                       "ORDER BY first_seen DESC LIMIT ?", (limit,)).fetchall()
    if not rows:
        print("nothing collected yet")
    for first_seen, source, company, title, url in rows:
        print(f"{first_seen[:16]}  {source:10} {company[:24]:24} {title[:44]:44} {url}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="poll and report, but write no files and send no notifications")
    ap.add_argument("--source", action="append", default=[],
                    help="restrict to this source (repeatable)")
    ap.add_argument("--recent", type=int, metavar="N",
                    help="list the last N collected offers and exit")
    ap.add_argument("--config", default=CONFIG)
    args = ap.parse_args()

    if args.recent:
        list_recent(args.recent)
        return 0

    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)

    enabled = [s for s in cfg.get("sources", []) if not args.source or s in args.source]
    if not enabled:
        print("no sources enabled", file=sys.stderr)
        return 1
    jobspy_sites = [s for s in enabled if s != "stepstone"]

    found = []
    for query in cfg.get("queries", []):
        print(f"\n> {query['term']} @ {query.get('location', 'anywhere')}")
        if jobspy_sites:
            found += from_jobspy(query, jobspy_sites, cfg)
        if "stepstone" in enabled:
            found += from_stepstone(query, cfg)

    min_chars = cfg.get("min_description_chars", 0)
    thin = [r for r in found if len(r.get("description") or "") < min_chars]
    found = [r for r in found if len(r.get("description") or "") >= min_chars]

    # richest version of a cross-posted job wins the alias slot
    found.sort(key=lambda r: len(r.get("description") or ""), reverse=True)

    con = open_state()
    known = {row[0] for row in con.execute("SELECT key FROM seen")}
    aliases = {row[0] for row in con.execute("SELECT akey FROM alias")}
    cross = cfg.get("cross_source_dedupe", True)

    fresh, dupes = [], 0
    for rec in found:
        key, akey = dedupe_key(rec), alias_key(rec)
        if key in known or (cross and akey in aliases):
            dupes += 1
            continue
        known.add(key)
        aliases.add(akey)
        fresh.append((key, akey, rec))

    print(f"\n{len(found) + len(thin)} scraped | {len(fresh)} new | {dupes} already known"
          + (f" | {len(thin)} skipped (description under {min_chars} chars)" if thin else ""))
    if not fresh:
        return 0

    records = []
    for key, akey, rec in fresh:
        path = write_offer(rec, key) if not args.dry_run else "(dry-run)"
        records.append(rec)
        if not args.dry_run:
            con.execute("INSERT OR REPLACE INTO seen VALUES (?,?,?,?,?,?,?)",
                        (key, rec["source"], rec["title"], rec["company"], rec["url"],
                         dt.datetime.now().isoformat(timespec="seconds"), path))
            con.execute("INSERT OR REPLACE INTO alias VALUES (?,?)", (akey, key))
    con.commit()
    notify(records, cfg, args.dry_run)
    if not args.dry_run:
        print(f"offers written to {INBOX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
