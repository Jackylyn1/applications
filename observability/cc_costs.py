#!/usr/bin/env python3
"""cc_costs - persistent, indexed cost store for Claude Code tasks + a fast reader.

Why this exists (and why it is NOT re-run by an AI each time):
  Pricing a transcript by hand every time is slow and error-prone. This script
  ingests Claude Code transcripts ONCE into a local SQLite database (indexed by
  session, turn, command and step), then reads costs back mechanically. Same
  numbers every time, no model in the loop.

Commands:

  ingest   Parse transcripts (main sessions + their subagents) and upsert one
           row per billed API response into observability/costs.db. Idempotent
           (keyed on message_id) and incremental - safe to re-run any time,
           including while a task is still generating.

      python cc_costs.py ingest --all
      python cc_costs.py ingest --latest
      python cc_costs.py ingest --session <id>

  report   One table: a row per task, with tokens, cost, time and the cache
           split. Pick the row granularity with --by, pick the rows with a
           scope flag.

      python cc_costs.py report                              # latest session, by step
      python cc_costs.py report --command generate-application
      python cc_costs.py report --command generate-application --runs --by command
      python cc_costs.py report --session <id> --by turn
      python cc_costs.py report --all --by model
      python cc_costs.py report --agent <id> --by call

  show     Alias for `report --by step` (a task and its substeps).
  tasks    Alias for `report --all --by session`.

Pricing (fresh input / cache read / cache write / output) is computed at ingest
time from pricing.json via cc_langfuse, and stored - so reads are pure SQL.
Re-run `ingest` after editing pricing.json to refresh stored costs.

Durations are derived, not billed: a transcript has no latency field, so a
call's time is the gap ending at its response (see cc_langfuse.call_durations).
Waiting on human input is never counted; waiting on a tool is not model time
either, which is why per-row time can be far below the wall-clock span.
"""

import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cc_langfuse as cc  # reuse the transcript parser + pricing

DEFAULT_DB = os.path.join(HERE, "costs.db")


# --------------------------------------------------------------------- db

ADDED_COLUMNS = [  # columns added after the first schema version
    ("prompt_id", "TEXT"),      # turn the call belongs to (subagents: parent turn)
    ("turn_label", "TEXT"),     # that turn's prompt text / '/command args'
    ("run_id", "TEXT"),         # command run the turn belongs to (see turn_map)
    ("command", "TEXT"),        # slash command that started that run, if any
    ("agent_type", "TEXT"),     # subagent type from the sibling .meta.json
    ("dur_s", "REAL"),          # generation time of this call, seconds
]


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent_id   TEXT,               -- NULL = main thread; else subagent id
            step       TEXT NOT NULL,      -- 'main' or 'agent:<id>'
            step_label TEXT,               -- human label for the step
            model      TEXT,
            ts         TEXT,
            in_tok     INTEGER, read_tok  INTEGER, write_tok  INTEGER, out_tok    INTEGER,
            in_cost    REAL,    read_cost REAL,    write_cost REAL,    out_cost   REAL,
            total_cost REAL,
            estimate   INTEGER,
            prompt_id  TEXT,               -- turn the call belongs to
            turn_label TEXT,               -- that turn's prompt / '/command args'
            run_id     TEXT,               -- command run the turn belongs to
            command    TEXT,               -- slash command of that run, if any
            agent_type TEXT,               -- subagent type, for subagent rows
            dur_s      REAL                -- generation time of this call, seconds
        )
    """)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(calls)")}
    for name, decl in ADDED_COLUMNS:      # migrate databases from before these
        if name not in have:
            conn.execute(f"ALTER TABLE calls ADD COLUMN {name} {decl}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_session ON calls(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_step    ON calls(session_id, step)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_agent   ON calls(agent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_cmd     ON calls(command, ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_prompt  ON calls(prompt_id)")
    conn.commit()
    return conn


# ----------------------------------------------------------------- ingest

def _agent_meta(path, agent_id):
    """(label, agent_type, tool_use_id) for a step. Main thread has no meta."""
    if agent_id is None:
        return "main thread (orchestrator)", None, None
    label = atype = tool_use_id = None
    # Sibling <path>.meta.json carries the Task call's description + toolUseId.
    meta = path[:-len(".jsonl")] + ".meta.json" if path.endswith(".jsonl") else None
    if meta and os.path.isfile(meta):
        try:
            d = json.load(open(meta))
            atype = (d.get("agentType") or d.get("subagent_type") or None)
            tool_use_id = d.get("toolUseId")
            for k in ("description", "summary", "name"):
                if isinstance(d.get(k), str) and d[k].strip():
                    label = d[k].strip()[:80]
                    break
        except Exception:
            pass
    if not label:
        # Fallback: first user text in the transcript (the prompt it was given).
        try:
            for line in open(path):
                o = json.loads(line)
                if o.get("type") == "user":
                    txt = cc._user_text(o.get("message", {}))
                    if txt:
                        label = txt[:80]
                        break
        except Exception:
            pass
    return label or f"agent {agent_id[:8]}", atype, tool_use_id


def ingest(conn, files, mults, models):
    """Upsert one row per billed API response, attributed to its turn.

    find_transcripts() yields each main transcript before its own subagents, so
    the parent turn index is always built before the subagents that need it.
    """
    n = 0
    turns = {"turns": {}, "tool_use": {}}    # index of the current main session
    for path, sid, aid in files:
        label, atype, tool_use_id = _agent_meta(path, aid)
        step = "main" if aid is None else f"agent:{aid}"
        if aid is None:
            turns = cc.turn_map(path)
        durs = cc.call_durations(path)
        # A subagent's whole run belongs to the turn whose Task call spawned it.
        parent = turns["turns"].get(turns["tool_use"].get(tool_use_id)) if aid else None

        for r in cc.parse_transcript(path, session_id=sid, agent_id=aid):
            turn = parent or turns["turns"].get(r["prompt_id"]) or {}
            p = cc.price_call(r["model"], r["usage"], mults, models)
            tk, co = p["tokens"], p["cost"]
            conn.execute(
                """INSERT OR REPLACE INTO calls (message_id, session_id, agent_id,
                   step, step_label, model, ts, in_tok, read_tok, write_tok, out_tok,
                   in_cost, read_cost, write_cost, out_cost, total_cost, estimate,
                   prompt_id, turn_label, run_id, command, agent_type, dur_s)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r["message_id"], sid, aid, step, label, r["model"], r.get("timestamp"),
                 tk["input"], tk["cache_read"], tk["cache_write"], tk["output"],
                 co["input"], co["cache_read"], co["cache_write"], co["output"],
                 co["total"], 1 if p["estimate"] else 0,
                 turn.get("prompt_id"), turn.get("title"), turn.get("run_id"),
                 turn.get("command"), atype, durs.get(r["message_id"])))
            n += 1
    conn.commit()
    return n


# ---------------------------------------------------------------- box table

def render(headers, aligns, rows, grid=True, rules=()):
    """Box table. grid=True separates every row; rules holds extra rule indexes."""
    cols = list(zip(*([headers] + rows))) if rows else [[h] for h in headers]
    widths = [max(len(str(c)) for c in col) for col in cols]

    def fmt(cells, fill=" "):
        out = []
        for cell, w, a in zip(cells, widths, aligns):
            s = str(cell)
            if a == "r":
                s = s.rjust(w)
            elif a == "c":
                s = s.center(w)
            else:
                s = s.ljust(w)
            out.append(f"{fill}{s}{fill}")
        return "│" + "│".join(out) + "│"

    def bar(l, m, r):
        return l + m.join("─" * (w + 2) for w in widths) + r

    lines = [bar("┌", "┬", "┐"), fmt(headers), bar("├", "┼", "┤")]
    for i, row in enumerate(rows):
        lines.append(fmt(row))
        last = i == len(rows) - 1
        if not last and (grid or (i + 1) in rules):
            lines.append(bar("├", "┼", "┤"))
    lines.append(bar("└", "┴", "┘"))
    return "\n".join(lines)


def _usd(x):
    x = x or 0.0
    return f"${x:,.4f}" if abs(x) < 0.01 else f"${x:,.2f}"


def _tok(n, exact=False):
    n = int(n or 0)
    if exact or n < 1000:
        return f"{n:,}"
    if n < 1_000_000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.2f}M"


def _model(name, count=1):
    if count > 1:
        return f"mixed ({count})"
    return (name or "?").replace("claude-", "")


def _clip(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ------------------------------------------------------------------- scope

def _match(conn, kind, prefix):
    """Expand an id prefix within one column. Returns the full id, or None."""
    rows = conn.execute(
        f"SELECT DISTINCT {kind}_id AS id FROM calls WHERE {kind}_id LIKE ?",
        (prefix + "%",)).fetchall()
    if len(rows) > 1:
        sys.exit(f"ambiguous {kind} prefix {prefix!r} matches {len(rows)} {kind}s")
    return rows[0]["id"] if rows else None


def resolve_task(conn, task):
    """Match a task id to a session or an agent (prefix). Returns (kind, id)."""
    for kind in ("session", "agent"):
        ident = _match(conn, kind, task)
        if ident:
            return (kind, ident)
    sys.exit(f"no task matching {task!r} in the db. Run `ingest` first, or `tasks`.")


GROUP_KEY = "COALESCE(run_id, prompt_id, session_id)"   # one logical piece of work


def _like_clause(text):
    """(sql, params) keeping whole runs that mention `text` anywhere in them."""
    if not text:
        return "", []
    pat = f"%{text.lower()}%"
    return (f"{GROUP_KEY} IN (SELECT {GROUP_KEY} FROM calls "
            f" WHERE lower(turn_label) LIKE ? OR lower(step_label) LIKE ?)",
            [pat, pat])


def resolve_scope(conn, a):
    """Turn the scope flags into (where_sql, params, human title)."""
    where, params, title = [], [], "all sessions"
    like_sql, like_params = _like_clause(getattr(a, "like", None))

    if getattr(a, "all", False):
        pass
    elif getattr(a, "command", None):
        cmd = a.command if a.command.startswith("/") else "/" + a.command
        if getattr(a, "runs", False):
            where.append("command = ?")
            params.append(cmd)
            title = f"{cmd}  (every ingested run)"
        else:
            # Bare run_id alongside MAX(ts) = the id from the latest matching row.
            row = conn.execute(
                "SELECT run_id, session_id, MAX(ts) AS ts FROM calls "
                "WHERE command = ?" + (f" AND {like_sql}" if like_sql else ""),
                [cmd] + like_params).fetchone()
            if not row or not row["run_id"]:
                sys.exit(f"no ingested run of {cmd}. Run `ingest --all` first, "
                         f"or `report --all --by command` to see what is there.")
            where.append("run_id = ?")
            params.append(row["run_id"])
            start = conn.execute("SELECT MIN(ts) AS ts FROM calls WHERE run_id = ?",
                                 (row["run_id"],)).fetchone()["ts"] or row["ts"]
            title = (f"{cmd}  last run, {start[:16].replace('T', ' ')}"
                     f"-{row['ts'][11:16]} UTC (session {row['session_id'][:8]})")
    elif getattr(a, "turn", None):
        where.append("prompt_id LIKE ?")
        params.append(a.turn + "%")
        title = f"turn {a.turn}"
    elif getattr(a, "session", None) or getattr(a, "agent", None) or getattr(a, "task", None):
        if getattr(a, "session", None) or getattr(a, "agent", None):
            kind = "session" if a.session else "agent"
            ident = _match(conn, kind, a.session or a.agent)
            if not ident:
                sys.exit(f"no {kind} matching {a.session or a.agent!r} in the db.")
        else:
            kind, ident = resolve_task(conn, a.task)
        where.append(f"{kind}_id = ?")
        params.append(ident)
        title = f"{kind} {ident}"
    else:                                  # default: the most recent session
        row = conn.execute(
            "SELECT session_id, MAX(ts) AS ts FROM calls").fetchone()
        if not row or not row["session_id"]:
            sys.exit("db is empty - run `ingest --all` first.")
        where.append("session_id = ?")
        params.append(row["session_id"])
        title = f"session {row['session_id']}  (latest)"

    if like_sql:
        where.append(like_sql)
        params += like_params
        title += f"  mentioning '{a.like}'"

    if getattr(a, "today", False):
        row = conn.execute("SELECT MAX(ts) AS ts FROM calls").fetchone()
        if row and row["ts"]:
            where.append("ts >= ?")
            params.append(row["ts"][:10])
            title += "  since " + row["ts"][:10]
    elif getattr(a, "since", None):
        where.append("ts >= ?")
        params.append(a.since)
        title += f"  since {a.since}"

    return (" AND ".join(where) or "1", params, title)


# ------------------------------------------------------------------ report

NO_CMD = "(no slash command)"

# by -> (group expression, label expression, default sort)
GROUPS = {
    "step":    ("session_id || '|' || step", "step_label", "cost"),
    "turn":    ("session_id || '|' || COALESCE(prompt_id, step)",
                "COALESCE(turn_label, step_label)", "ts"),
    "run":     (f"COALESCE(run_id, session_id || '|' || COALESCE(prompt_id, step))",
                f"COALESCE(command, turn_label, step_label)", "ts"),
    "command": (f"COALESCE(command, '{NO_CMD}')", f"COALESCE(command, '{NO_CMD}')", "cost"),
    "agent":   ("COALESCE(agent_id, 'main')", "step_label", "cost"),
    "model":   ("model", "model", "cost"),
    "session": ("session_id", "session_id", "ts"),
    "call":    ("message_id", "step_label", "ts"),
}

SORTS = {"cost": lambda r: -(r["cost"] or 0), "time": lambda r: -(r["dur"] or 0),
         "tokens": lambda r: -r["tok"], "calls": lambda r: -r["n"],
         "ts": lambda r: r["t0"] or ""}


def query(conn, where, params, by):
    gexpr, lexpr, _ = GROUPS[by]
    rows = conn.execute(f"""
        SELECT {gexpr} AS gkey, {lexpr} AS label,
               MIN(step) AS step, MIN(agent_type) AS agent_type,
               MIN(session_id) AS session_id, MIN(command) AS command,
               COUNT(*) AS n,
               COUNT(DISTINCT COALESCE(run_id, prompt_id, session_id)) AS runs,
               COUNT(DISTINCT model) AS nmodels, MIN(model) AS model,
               SUM(in_tok) AS in_tok, SUM(read_tok) AS read_tok,
               SUM(write_tok) AS write_tok, SUM(out_tok) AS out_tok,
               SUM(total_cost) AS cost, SUM(COALESCE(dur_s, 0)) AS dur,
               MIN(ts) AS t0, MAX(ts) AS t1, MAX(estimate) AS est
        FROM calls WHERE {where} GROUP BY gkey""", params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tok"] = sum(d[c] or 0 for c in ("in_tok", "read_tok", "write_tok", "out_tok"))
        out.append(d)
    return out


def report(conn, where, params, title, by="step", sort=None, exact=False,
           width=42, fmt="text", limit=None):
    rows = query(conn, where, params, by)
    if not rows:
        sys.exit(f"no calls in scope ({title}). Run `ingest --all` first.")

    sort = sort or GROUPS[by][2]
    rows.sort(key=SORTS[sort])
    if by == "step":                        # keep the orchestrator on top
        rows.sort(key=lambda r: r["step"] != "main")

    # Totals cover the whole scope even when only the top N rows are printed.
    tot = {k: sum(r[k] or 0 for r in rows)
           for k in ("n", "in_tok", "read_tok", "write_tok", "out_tok", "tok",
                     "cost", "dur")}
    hidden = 0
    if limit and len(rows) > limit:
        hidden = len(rows) - limit
        rows = rows[:limit]
    span0 = min((r["t0"] for r in rows if r["t0"]), default=None)
    span1 = max((r["t1"] for r in rows if r["t1"]), default=None)
    span = None
    if span0 and span1:
        a, b = cc._parse_ts(span0), cc._parse_ts(span1)
        span = (b - a).total_seconds() if a and b else None

    if fmt == "json":
        print(json.dumps({"scope": title, "by": by, "rows": rows,
                          "total": tot, "span_s": span}, indent=2, default=str))
        return

    show_runs = by in ("command", "session")
    head = ["task", "model", "calls"] + (["runs"] if show_runs else []) + \
           ["time", "fresh in", "cache rd", "cache wr", "output", "tokens", "cost", "%"]
    align = ["l", "l", "r"] + (["r"] if show_runs else []) + ["r"] * 9
    body = []
    for r in rows:
        label = _clip(r["label"] or r["gkey"], width)
        if by == "step" and r["step"] != "main":
            label = "↳ " + _clip(r["label"] or r["gkey"], width - 2)
        elif by == "call":
            label = f"{(r['t0'] or '')[11:19]}  " + _clip(r["label"], width - 10)
        elif by in ("turn", "run"):     # same prompt text can recur - date it
            label = f"{(r['t0'] or '')[5:16].replace('T', ' ')}  " + \
                    _clip(r["label"] or r["gkey"], width - 13)
        cells = [label, _model(r["model"], r["nmodels"]), f"{r['n']:,}"]
        if show_runs:
            cells.append(f"{r['runs']:,}")
        cells += [cc._fmt_dur(r["dur"]),
                  _tok(r["in_tok"], exact), _tok(r["read_tok"], exact),
                  _tok(r["write_tok"], exact), _tok(r["out_tok"], exact),
                  _tok(r["tok"], exact), _usd(r["cost"]),
                  f"{(r['cost'] or 0) / tot['cost'] * 100:.1f}" if tot["cost"] else "0.0"]
        body.append(cells)

    total_cells = ["TOTAL", "", f"{tot['n']:,}"]
    if show_runs:
        total_cells.append(f"{sum(r['runs'] for r in rows):,}")
    total_cells += [cc._fmt_dur(tot["dur"]),
                    _tok(tot["in_tok"], exact), _tok(tot["read_tok"], exact),
                    _tok(tot["write_tok"], exact), _tok(tot["out_tok"], exact),
                    _tok(tot["tok"], exact), _usd(tot["cost"]), "100.0"]
    body.append(total_cells)

    shown = f"{len(rows)} row(s)" + (f" of {len(rows) + hidden}" if hidden else "")
    print(f"\n{title}   —   by {by}, {shown}\n")
    print(render(head, align, body, grid=False, rules={len(body) - 1}))
    if hidden:
        print(f"  ({hidden} row(s) hidden by --limit; TOTAL still covers all of them)")

    prompt_side = tot["in_tok"] + tot["read_tok"] + tot["write_tok"]
    hit = tot["read_tok"] / prompt_side * 100 if prompt_side else 0.0
    bits = [f"model time {cc._fmt_dur(tot['dur'])}"]
    if span is not None:
        bits.append(f"wall span {cc._fmt_dur(span)}")
    bits.append(f"cache hit {hit:.1f}%")
    if tot["dur"]:
        bits.append(f"{tot['out_tok'] / tot['dur']:.0f} out tok/s")
        bits.append(f"{_usd(tot['cost'] / (tot['dur'] / 60))}/min of model time")
    print("  " + "  |  ".join(bits))

    if any(r["est"] for r in rows):
        print("  ! includes estimated pricing (see pricing.json)")
    stale = conn.execute(
        f"SELECT COUNT(*) c FROM calls WHERE ({where}) AND prompt_id IS NULL",
        params).fetchone()["c"]
    if stale:
        print(f"  ! {stale} call(s) predate turn tracking - re-run "
              f"`ingest --all` to attribute them to a turn/command")


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="parse transcripts into the db")
    g = ing.add_mutually_exclusive_group()
    g.add_argument("--latest", action="store_true")
    g.add_argument("--all", action="store_true")
    g.add_argument("--session", metavar="ID")
    ing.add_argument("--project-dir", default=cc.DEFAULT_PROJECT_DIR)
    ing.add_argument("--pricing", default=cc.DEFAULT_PRICING)

    rep = sub.add_parser("report", help="one table: tokens, cost, time per task")
    rep.add_argument("task", nargs="?", help="session or agent id (prefix ok)")
    scope = rep.add_mutually_exclusive_group()
    scope.add_argument("--session", metavar="ID", help="one session (a terminal)")
    scope.add_argument("--agent", metavar="ID", help="one subagent")
    scope.add_argument("--command", metavar="NAME",
                       help="a slash command, e.g. generate-application "
                            "(last run unless --runs)")
    scope.add_argument("--turn", metavar="PROMPT_ID", help="one user turn")
    scope.add_argument("--all", action="store_true", help="everything in the db")
    scope.add_argument("--latest", action="store_true", help="newest session (default)")
    rep.add_argument("--runs", action="store_true",
                     help="with --command: every run, not just the last")
    rep.add_argument("--like", metavar="TEXT",
                     help="keep only runs that mention TEXT in a prompt or a "
                          "step name (e.g. an employer) - whole run, not just "
                          "the matching rows")
    rep.add_argument("--by", choices=sorted(GROUPS), default="step",
                     help="row granularity (default: step)")
    rep.add_argument("--sort", choices=sorted(SORTS), help="default depends on --by")
    rep.add_argument("--since", metavar="ISO", help="only calls at/after this time")
    rep.add_argument("--today", action="store_true", help="only the newest day of data")
    rep.add_argument("--limit", type=int, help="keep only the top N rows")
    rep.add_argument("--exact", action="store_true", help="full token counts, no k/M")
    rep.add_argument("--width", type=int, default=42, help="task column width")
    rep.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="alias: report --by step")
    sh.add_argument("task", nargs="?")
    sh.add_argument("--latest", action="store_true")

    sub.add_parser("tasks", help="alias: report --all --by session")

    args = ap.parse_args()
    conn = connect(args.db)

    if args.cmd == "ingest":
        mults, models = cc.load_pricing(args.pricing)
        which = "latest" if args.latest or not (args.all or args.session) else "all"
        files = cc.find_transcripts(args.project_dir, which, args.session)
        n = ingest(conn, files, mults, models)
        print(f"ingested {n} API calls from {len(files)} transcript(s) into {args.db}")
        return

    if args.cmd == "show":
        args.session = args.agent = args.command = args.turn = None
        args.all = False
        args.by, args.sort, args.since, args.today = "step", None, None, False
        args.limit, args.exact, args.width, args.json = None, False, 42, False
    elif args.cmd == "tasks":
        args.task = args.session = args.agent = args.command = args.turn = None
        args.all, args.latest, args.runs = True, False, False
        args.by, args.sort, args.since, args.today = "session", None, None, False
        args.limit, args.exact, args.width, args.json = None, False, 42, False

    where, params, title = resolve_scope(conn, args)
    report(conn, where, params, title, by=args.by, sort=args.sort,
           exact=args.exact, width=args.width,
           fmt="json" if args.json else "text", limit=args.limit)


if __name__ == "__main__":
    main()
