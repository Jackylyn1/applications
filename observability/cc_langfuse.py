#!/usr/bin/env python3
"""cc_langfuse - attribute Claude Code token cost and ship it to Langfuse.

This project's AI work runs through Claude Code (the CLI orchestrating the
career-kb / job-watch skills and subagents), not through direct Anthropic API
calls in our own code - so there is nothing in the codebase for the Langfuse
SDK to wrap at request time. What we CAN observe is where the tokens actually
go: Claude Code writes every session as a JSONL transcript, and every assistant
turn carries a `usage` block (fresh input, cache-read, cache-creation, output).

This tool reads those transcripts, prices each turn with the correct per-model
and cache-tier rates (pricing.json), and exports one Langfuse trace per
user-prompt turn - grouped into a Langfuse session per Claude Code session - so
cost is attributable by prompt, by cache read vs write, by growing context, by
model, and by session.

Usage:
    # Local breakdown, no Langfuse account needed (stdlib only):
    python cc_langfuse.py --report --latest
    python cc_langfuse.py --report --all

    # See exactly what would be sent, without sending it:
    python cc_langfuse.py --dry-run --latest

    # Export to Langfuse (reads LANGFUSE_* from env / .env):
    python cc_langfuse.py --latest
    python cc_langfuse.py --all
    python cc_langfuse.py --session <session-id>

Idempotent: traces/generations use deterministic ids derived from the session
and request ids, so re-running updates in place instead of duplicating.
"""

import argparse
import re
import datetime as dt
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRICING = os.path.join(HERE, "pricing.json")

# Where Claude Code stores this project's session transcripts.
DEFAULT_PROJECT_DIR = os.path.expanduser(
    "~/.claude/projects/-home-jacqueline-Desktop-applications"
)


# ----------------------------------------------------------------- pricing

def load_pricing(path):
    with open(path) as f:
        data = json.load(f)
    return data.get("cache_multipliers", {}), data.get("models", {})


def resolve_rate(model, models):
    """Match a transcript model id to a pricing entry.

    Transcript ids carry decorations the price list does not:
    a dated release suffix (`claude-haiku-4-5-20251001`) and a context-window
    tag (`claude-opus-5[1m]`). Matching only on the exact string silently drops
    such a model onto `default` - which priced Haiku at Opus rates, a 5x
    overstatement. Strip the decorations before giving up.
    """
    for candidate in (model,
                      re.sub(r"\[.*?\]$", "", model or ""),
                      re.sub(r"-\d{8}$", "", re.sub(r"\[.*?\]$", "", model or ""))):
        if candidate in models:
            return models[candidate], candidate
    return models.get("default", {}), None


def price_call(model, usage, mults, models):
    """Return a cost/token breakdown dict for one assistant API call.

    Keys mirror the question 'where does the cost come from':
      input        - fresh, uncached prompt tokens (context you paid full price for)
      cache_read   - tokens served from cache (~0.1x)
      cache_write  - tokens written to cache (~1.25x for 5m, ~2x for 1h)
      output       - generated tokens
    """
    rate, matched = resolve_rate(model, models)
    in_rate = rate.get("input", 0.0)
    out_rate = rate.get("output", 0.0)
    estimate = bool(rate.get("_estimate")) or matched is None

    fresh = usage.get("input_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    cache_create = usage.get("cache_creation_input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0

    # Split cache creation into 5m / 1h tiers when the breakdown is present.
    breakdown = usage.get("cache_creation") or {}
    tier_5m = breakdown.get("ephemeral_5m_input_tokens")
    tier_1h = breakdown.get("ephemeral_1h_input_tokens")
    if tier_5m is None and tier_1h is None:
        tier_5m, tier_1h = cache_create, 0  # assume 5m when untiered

    per = 1_000_000.0
    input_cost = fresh / per * in_rate
    read_cost = cache_read / per * in_rate * mults.get("read", 0.1)
    write_cost = (
        (tier_5m or 0) / per * in_rate * mults.get("write_5m", 1.25)
        + (tier_1h or 0) / per * in_rate * mults.get("write_1h", 2.0)
    )
    output_cost = out / per * out_rate
    total = input_cost + read_cost + write_cost + output_cost

    return {
        "model": model,
        "estimate": estimate,
        "tokens": {
            "input": fresh,
            "cache_read": cache_read,
            "cache_write": cache_create,
            "output": out,
        },
        "cost": {
            "input": input_cost,
            "cache_read": read_cost,
            "cache_write": write_cost,
            "output": output_cost,
            "total": total,
        },
    }


# ------------------------------------------------------------- transcripts

def _subagent_files(project_dir, session_id):
    """Subagent transcripts live beside the main one, not inside it.

    Claude Code writes each Task/subagent run to
        <project_dir>/<session_id>/subagents/agent-<agentId>.jsonl
    with `isSidechain: true`. They are NOT folded into the main transcript, so
    a tool that only globs <project_dir>/*.jsonl sees none of the subagent
    cost or time - which for an orchestrated pipeline is most of both.
    """
    d = os.path.join(project_dir, session_id, "subagents")
    if not os.path.isdir(d):
        return []
    return [
        (os.path.join(d, f), session_id, f[len("agent-"):-len(".jsonl")])
        for f in sorted(os.listdir(d))
        if f.startswith("agent-") and f.endswith(".jsonl")
    ]


def find_transcripts(project_dir, which, session=None, subagents=True):
    """Return [(path, session_id, agent_id_or_None)] for the selection."""
    if not os.path.isdir(project_dir):
        sys.exit(f"No Claude Code project dir at {project_dir}")
    files = [
        os.path.join(project_dir, f)
        for f in os.listdir(project_dir)
        if f.endswith(".jsonl")
    ]
    if not files:
        sys.exit(f"No .jsonl transcripts under {project_dir}")

    if session:
        picked = [f for f in files if os.path.basename(f).startswith(session)]
        if not picked:
            sys.exit(f"No transcript matching session {session!r}")
    elif which == "latest":
        picked = [max(files, key=os.path.getmtime)]
    else:
        picked = sorted(files, key=os.path.getmtime)

    out = []
    for path in picked:
        sid = os.path.splitext(os.path.basename(path))[0]
        out.append((path, sid, None))
        if subagents:
            out.extend(_subagent_files(project_dir, sid))
    return out


def _user_text(message):
    """Best-effort short label for a user prompt; skip pure tool-result turns."""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts).strip()
    return ""


_SLASH_RE = re.compile(r"<command-name>\s*(/[\w:.-]+)", re.I)
_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S | re.I)


def command_of(text):
    """Return the slash command a user prompt invoked ('/foo'), else None."""
    if not text:
        return None
    m = _SLASH_RE.search(text)
    if m:
        return m.group(1).lower()
    s = text.lstrip()
    if s.startswith("/"):
        return s.split()[0].lower()
    return None


def turn_title(text, limit=70):
    """Short human label for a turn: '/cmd args' for commands, else the prompt."""
    cmd = command_of(text)
    if cmd:
        m = _ARGS_RE.search(text or "")
        args = " ".join(m.group(1).split()) if m else ""
        return f"{cmd} {args}".strip()[:limit]
    if "<task-notification>" in (text or ""):
        return "(background agent finished)"
    return " ".join((text or "").split())[:limit] or "session start"


_REF_RE = re.compile(r"<tool-use-id>\s*([\w-]+)\s*</tool-use-id>", re.I)
AGENT_TOOLS = {"Agent", "Task"}     # the tool that spawns a subagent
RUN_GAP_S = 1800.0                  # 30 min: how long a run may sit idle


def turn_map(path, gap_s=RUN_GAP_S):
    """Index a main transcript's turns and group them into command runs.

    Returns {'turns': {prompt_id: {...}}, 'tool_use': {tool_use_id: prompt_id}}.
    The tool_use index ties a subagent back to the turn that spawned it: each
    subagent's sibling .meta.json carries that Agent call's toolUseId.

    A slash command's work rarely fits in its own turn - the human answers a
    question, and every finished background agent comes back as a fresh turn.
    So a RUN spans from the command turn to the last turn it caused, and every
    turn in between belongs to it. A turn extends the open run when it either
    reports a result from an agent the run spawned (<tool-use-id> back-
    reference - always causal) or spawns an agent itself within gap_s of the
    run's last activity. Nothing else is pulled in, so a later unrelated
    question is never billed to the command.
    """
    turns, tool_use, order = {}, {}, []
    cur = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = o.get("type")
            if t == "user":
                pid = o.get("promptId")
                if not pid:
                    continue          # tool results and local-only commands
                if pid not in turns:
                    text = _user_text(o.get("message", {}))
                    turns[pid] = {
                        "prompt_id": pid, "index": len(order) + 1,
                        "title": turn_title(text), "own_command": command_of(text),
                        "command": None, "run_id": None,
                        "ts": o.get("timestamp"), "last_ts": o.get("timestamp"),
                        "issues": set(), "spawns": set(), "refs": set(),
                    }
                    order.append(pid)
                cur = pid
                turns[pid]["refs"].update(_REF_RE.findall(_user_text(o.get("message", {}))))
            if cur and o.get("timestamp"):
                turns[cur]["last_ts"] = o["timestamp"]
            if t == "assistant" and cur:
                for c in o.get("message", {}).get("content", []) or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("id"):
                        tool_use[c["id"]] = cur
                        turns[cur]["issues"].add(c["id"])
                        if c.get("name") in AGENT_TOOLS:
                            turns[cur]["spawns"].add(c["id"])

    _assemble_runs(turns, order, gap_s)
    return {"turns": turns, "tool_use": tool_use}


def _assemble_runs(turns, order, gap_s):
    """Second pass: attach each turn to the command run it belongs to."""
    run, issued, pending, last_ts = None, set(), [], None
    for pid in order:
        t = turns[pid]
        if t["own_command"]:
            run, issued, pending = pid, set(t["issues"]), []
            t["run_id"], t["command"] = pid, t["own_command"]
            last_ts = t["last_ts"]
            continue
        if run is None:
            continue
        gap = _gap_s(last_ts, t["ts"])
        if (t["refs"] & issued) or (t["spawns"] and gap is not None and gap <= gap_s):
            for p in pending:      # turns sandwiched inside the run come along
                turns[p]["run_id"] = run
                turns[p]["command"] = turns[run]["command"]
            pending = []
            t["run_id"], t["command"] = run, turns[run]["command"]
            issued |= t["issues"]
            last_ts = t["last_ts"]
        else:                      # keep it aside; a later result may claim it
            pending.append(pid)
            issued |= t["issues"]


def _gap_s(a, b):
    ta, tb = _parse_ts(a), _parse_ts(b)
    return (tb - ta).total_seconds() if ta and tb else None


def call_durations(path):
    """Return {message_id: seconds} - generation time per assistant response.

    Transcripts carry no latency field, so it is derived the same way
    analyze_timing() does: the gap ENDING at an assistant response is the time
    that response took. A streamed response spans several lines sharing one
    message.id, so the window runs from the last preceding non-assistant event
    to that message's final line. Gaps before user prompts are never counted,
    so human think time stays out of the number.
    """
    out, starts = {}, {}
    prev = None          # ts of the last event that closed a window
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(o.get("timestamp"))
            if not ts:
                continue
            if o.get("type") == "assistant":
                mid = (o.get("message", {}) or {}).get("id")
                if not mid:
                    continue
                if mid not in starts:
                    starts[mid] = prev or ts
                    cur_mid = mid
                out[mid] = max((ts - starts[mid]).total_seconds(), 0.0)
                prev = ts
            else:
                prev = ts
    return out


def parse_transcript(path, session_id=None, agent_id=None):
    """Yield one record per assistant API call, tagged with its turn.

    A 'turn' is a distinct promptId (one user prompt). Assistant calls inherit
    the most recently seen promptId in file order, which groups an agentic
    loop's tool round-trips under the prompt that started it.
    """
    if session_id is None:
        session_id = os.path.splitext(os.path.basename(path))[0]
    cur_prompt = None
    turn_index = 0
    seen_prompts = set()
    records = {}   # message.id -> record (usage kept from the completed line)
    order = []
    turn_labels = {}

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = o.get("type")
            if t == "user":
                pid = o.get("promptId")
                if pid and pid not in seen_prompts:
                    seen_prompts.add(pid)
                    turn_index += 1
                    label = _user_text(o.get("message", {}))
                    turn_labels[pid] = label[:100] if label else f"turn {turn_index}"
                if pid:
                    cur_prompt = pid
                continue

            if t != "assistant":
                continue

            msg = o.get("message", {})
            model = msg.get("model")
            usage = msg.get("usage")
            if not model or model == "<synthetic>" or not isinstance(usage, dict):
                continue

            # Claude Code logs a streaming assistant response on several lines
            # that share one message.id: early lines carry partial usage (a few
            # output tokens), the final line the complete usage. Collapse to the
            # message.id and keep the line with the MOST output tokens - the
            # completed one - or output (and its $25/M cost) is undercounted
            # many-fold.
            mid = msg.get("id") or o.get("requestId") or o.get("uuid")
            out = usage.get("output_tokens", 0) or 0
            rec = records.get(mid)
            if rec is None:
                records[mid] = {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "prompt_id": cur_prompt or "no-prompt",
                    "message_id": mid,
                    "timestamp": o.get("timestamp"),
                    "model": model,
                    "effort": o.get("effort"),
                    "usage": usage,
                    "_out": out,
                }
                order.append(mid)
            elif out > rec["_out"]:
                rec["usage"] = usage
                rec["_out"] = out

    for mid in order:
        rec = records.pop(mid)
        rec.pop("_out", None)
        rec["turn_label"] = turn_labels.get(rec["prompt_id"], "session start")
        yield rec


def _parse_ts(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------- timing

def _fmt_dur(seconds):
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(round(seconds)), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def timeline(path):
    """Yield (timestamp, kind, name) events in file order.

    kind is one of:
      'prompt'      a user prompt starting a turn
      'assistant'   an assistant API response completed
      'tool_result' a tool finished and its result came back

    Timestamps mark when each event was written, so the gap ENDING at an
    event is the time that event took: gap before an 'assistant' event is
    model latency, gap before a 'tool_result' is tool execution.
    """
    pending = {}   # tool_use id -> label, so a result can name its own tool
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(o.get("timestamp"))
        if not ts:
            continue
        t = o.get("type")
        if t == "assistant":
            msg = o.get("message", {})
            names = []
            for c in msg.get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    name = c.get("name") or "tool"
                    inp = c.get("input") or {}
                    detail = inp.get("command") or inp.get("file_path") or ""
                    pending[c.get("id")] = f"{name}({str(detail)[:60]})" if detail else name
                    names.append(name)
            yield ts, "assistant", ",".join(names) or "text"
        elif t == "user":
            if o.get("toolUseResult") is not None:
                label = ""
                content = o.get("message", {}).get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result":
                            label = pending.pop(c.get("tool_use_id"), "")
                yield ts, "tool_result", label or "tool"
            elif o.get("promptId"):
                yield ts, "prompt", _user_text(o.get("message", {}))[:70]


def analyze_timing(path):
    """Split a transcript's wall clock into model time vs tool time."""
    events = list(timeline(path))
    if len(events) < 2:
        return None
    model_s = tool_s = other_s = 0.0
    slowest = []
    prev = events[0][0]
    for ts, kind, name in events[1:]:
        gap = (ts - prev).total_seconds()
        prev = ts
        if kind == "assistant":
            model_s += gap
            slowest.append((gap, "model", name))
        elif kind == "tool_result":
            tool_s += gap
            slowest.append((gap, "tool", name))
        else:
            other_s += gap
    slowest.sort(reverse=True)
    return {
        "start": events[0][0],
        "end": events[-1][0],
        "span_s": (events[-1][0] - events[0][0]).total_seconds(),
        "model_s": model_s,
        "tool_s": tool_s,
        "idle_s": other_s,
        "events": len(events),
        "slowest": slowest[:8],
    }


def timing_report(entries):
    """entries: [(path, session_id, agent_id)] - print a wall-clock breakdown."""
    mains = [e for e in entries if e[2] is None]
    agents = [e for e in entries if e[2] is not None]

    for path, sid, _ in mains:
        a = analyze_timing(path)
        if not a:
            continue
        print(f"\n=== session {sid[:8]} - wall clock ===")
        print(f"  span          {_fmt_dur(a['span_s'])}   "
              f"({a['start']:%H:%M:%S} -> {a['end']:%H:%M:%S} UTC)")
        print(f"  model time    {_fmt_dur(a['model_s'])}")
        print(f"  tool time     {_fmt_dur(a['tool_s'])}")
        print(f"  idle/waiting  {_fmt_dur(a['idle_s'])}   "
              f"(includes waiting on user input and on background agents)")

    if not agents:
        return
    print(f"\n=== subagents ({len(agents)}) - these run inside the parent's "
          f"'idle' time ===")
    rows = []
    for path, sid, aid in agents:
        a = analyze_timing(path)
        if not a:
            continue
        rows.append((a["span_s"], aid, a))
    rows.sort(reverse=True)
    total = sum(r[0] for r in rows)
    for span, aid, a in rows:
        print(f"  {aid[:12]:<14} {_fmt_dur(span):>8}   "
              f"model {_fmt_dur(a['model_s']):>7} | tool {_fmt_dur(a['tool_s']):>7} | "
              f"{a['events']:>3} events")
        for gap, kind, name in a["slowest"][:3]:
            print(f"       slowest: {kind:<6} {name[:44]:<46} {_fmt_dur(gap)}")
    print(f"  {'-'*58}")
    print(f"  sum of subagent spans: {_fmt_dur(total)} "
          f"(wall clock is less when they run in parallel)")


# ---------------------------------------------------------------- report

def _fmt_usd(x):
    return f"${x:,.4f}"


def report(records, mults, models):
    by_session = defaultdict(list)
    for r in records:
        by_session[r["session_id"]].append(r)

    grand = defaultdict(float)
    grand_tokens = defaultdict(int)
    est_models = set()

    for sid, recs in by_session.items():
        s_cost = defaultdict(float)
        s_tok = defaultdict(int)
        by_model = defaultdict(lambda: defaultdict(float))
        for r in recs:
            p = price_call(r["model"], r["usage"], mults, models)
            if p["estimate"]:
                est_models.add(r["model"])
            for k, v in p["cost"].items():
                s_cost[k] += v
                if k != "total":
                    grand[k] += v
                by_model[r["model"]]["total"] += v if k == "total" else 0
            for k, v in p["tokens"].items():
                s_tok[k] += v
                grand_tokens[k] += v

        print(f"\n=== session {sid[:8]}  ({len(recs)} calls) ===")
        print(f"  input (fresh) : {s_tok['input']:>12,} tok   {_fmt_usd(s_cost['input'])}")
        print(f"  cache read    : {s_tok['cache_read']:>12,} tok   {_fmt_usd(s_cost['cache_read'])}")
        print(f"  cache write   : {s_tok['cache_write']:>12,} tok   {_fmt_usd(s_cost['cache_write'])}")
        print(f"  output        : {s_tok['output']:>12,} tok   {_fmt_usd(s_cost['output'])}")
        print(f"  {'-'*46}")
        print(f"  session total : {_fmt_usd(s_cost['total'])}")
        for m, c in sorted(by_model.items(), key=lambda kv: -kv[1]['total']):
            print(f"      {m:<22} {_fmt_usd(c['total'])}")

    total = sum(grand.values())
    prompt_side = grand["input"]
    cache_side = grand["cache_read"] + grand["cache_write"]
    print(f"\n{'='*52}")
    print("GRAND TOTAL - where the cost comes from")
    print(f"{'='*52}")
    tot_tokens = sum(grand_tokens.values()) or 1
    for label, ck, tk in [
        ("fresh input (prompts+context)", "input", "input"),
        ("cache read", "cache_read", "cache_read"),
        ("cache write", "cache_write", "cache_write"),
        ("output", "output", "output"),
    ]:
        share = grand[ck] / total * 100 if total else 0
        print(f"  {label:<32} {_fmt_usd(grand[ck])}  ({share:4.1f}% of $)   "
              f"{grand_tokens[tk]:>12,} tok")
    read_tok = grand_tokens["cache_read"]
    ctx_tok = grand_tokens["input"] + read_tok
    hit = read_tok / ctx_tok * 100 if ctx_tok else 0
    print(f"  {'-'*48}")
    print(f"  TOTAL {_fmt_usd(total)}")
    print(f"  prompt/context vs caching: {_fmt_usd(prompt_side)} fresh  |  "
          f"{_fmt_usd(cache_side)} cache")
    print(f"  cache hit rate (read / prompt-side tokens): {hit:.1f}%")
    if est_models:
        print(f"\n  ! estimated pricing used for: {', '.join(sorted(est_models))}")
        print("    Correct these in pricing.json against platform.claude.com/pricing.")


# ---------------------------------------------------------------- export

def export(records, mults, models, dry_run=False):
    lf = None
    if not dry_run:
        try:
            from langfuse import Langfuse
        except ImportError:
            sys.exit("langfuse not installed. Run: pip install -r "
                     "observability/requirements.txt  (or use --report / --dry-run)")
        pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
        sk = os.environ.get("LANGFUSE_SECRET_KEY")
        if not (pk and sk):
            sys.exit("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                     "(see observability/.env.example).")
        lf = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )

    # Group calls into (session, prompt) turns -> one Langfuse trace each.
    # Subagent calls get their own trace per (session, agent, prompt) so a
    # pipeline's phases stay separable instead of collapsing into the parent.
    turns = defaultdict(list)
    for r in records:
        turns[(r["session_id"], r.get("agent_id"), r["prompt_id"])].append(r)

    n_traces = n_gens = 0
    for (sid, aid, pid), recs in turns.items():
        recs.sort(key=lambda r: r.get("timestamp") or "")
        trace_id = f"cc-{sid}-{aid or 'main'}-{pid}"
        ts = [_parse_ts(r["timestamp"]) for r in recs]
        ts = [t for t in ts if t]
        start = min(ts) if ts else None

        priced = [price_call(r["model"], r["usage"], mults, models) for r in recs]
        turn_total = sum(p["cost"]["total"] for p in priced)
        turn_meta = {
            "claude_code_session": sid,
            "agent_id": aid,
            "prompt_id": pid,
            "calls": len(recs),
            "models": sorted({r["model"] for r in recs}),
            "turn_cost_usd": round(turn_total, 6),
            "cost_usd": {
                k: round(sum(p["cost"][k] for p in priced), 6)
                for k in ("input", "cache_read", "cache_write", "output")
            },
            "tokens": {
                k: sum(p["tokens"][k] for p in priced)
                for k in ("input", "cache_read", "cache_write", "output")
            },
        }
        label = recs[0]["turn_label"]

        if dry_run:
            print(f"[trace] {trace_id}  session={sid[:8]}  "
                  f"{_fmt_usd(turn_total)}  {label[:60]!r}")
        else:
            lf.trace(
                id=trace_id,
                name=label or "turn",
                session_id=sid,
                timestamp=start,
                input=label,
                tags=["claude-code"] + (["subagent", f"agent:{aid}"] if aid else ["main"]),
                metadata=turn_meta,
            )
        n_traces += 1

        # A transcript timestamp marks when a response COMPLETED, so a call's
        # latency is the gap since the previous event in the same turn. Without
        # this every generation would be start==end and Langfuse would render
        # the whole pipeline as zero-duration - useless for finding slow steps.
        prev_end = start
        for r, p in zip(recs, priced):
            gen_id = f"cc-{r['message_id']}"
            when = _parse_ts(r["timestamp"])
            began = prev_end if (prev_end and when and prev_end <= when) else when
            prev_end = when or prev_end
            tk = p["tokens"]
            usage_details = {
                "input": tk["input"],
                "cache_read": tk["cache_read"],
                "cache_write": tk["cache_write"],
                "output": tk["output"],
                "total": tk["input"] + tk["cache_read"] + tk["cache_write"]
                + tk["output"],
            }
            cost_details = {
                "input": p["cost"]["input"],
                "cache_read": p["cost"]["cache_read"],
                "cache_write": p["cost"]["cache_write"],
                "output": p["cost"]["output"],
                "total": p["cost"]["total"],
            }
            latency = (when - began).total_seconds() if (when and began) else None
            gen_meta = {
                "effort": r.get("effort"),
                "agent_id": aid,
                "estimated_pricing": p["estimate"],
                "latency_s": round(latency, 3) if latency is not None else None,
                "tokens": p["tokens"],
                "cost_usd": {k: round(v, 6) for k, v in p["cost"].items()},
            }
            if dry_run:
                print(f"    [gen] {r['model']:<20} {_fmt_usd(p['cost']['total'])}  "
                      f"{_fmt_dur(latency):>7}  "
                      f"in={p['tokens']['input']} read={p['tokens']['cache_read']} "
                      f"write={p['tokens']['cache_write']} out={p['tokens']['output']}"
                      + ("  (est)" if p["estimate"] else ""))
            else:
                lf.generation(
                    id=gen_id,
                    trace_id=trace_id,
                    name=r["model"],
                    model=r["model"],
                    start_time=began,
                    end_time=when,
                    usage_details=usage_details,
                    cost_details=cost_details,
                    metadata=gen_meta,
                )
            n_gens += 1

    if dry_run:
        print(f"\nWould send {n_traces} traces / {n_gens} generations to Langfuse.")
    else:
        lf.flush()
        print(f"Sent {n_traces} traces / {n_gens} generations to "
              f"{os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")


# ------------------------------------------------------------------ main

def load_dotenv(path):
    """Minimal .env loader (no dependency) - only sets keys not already in env."""
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for raw in f:
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, v = raw.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--latest", action="store_true",
                     help="only the most recent session transcript")
    sel.add_argument("--all", action="store_true",
                     help="every session transcript for this project")
    sel.add_argument("--session", metavar="ID",
                     help="a specific session id (prefix match)")
    ap.add_argument("--report", action="store_true",
                    help="print a local cost breakdown; do not touch Langfuse")
    ap.add_argument("--timing", action="store_true",
                    help="print a local wall-clock breakdown (model vs tool vs "
                         "idle, per subagent); do not touch Langfuse")
    ap.add_argument("--no-subagents", action="store_true",
                    help="ignore subagent transcripts (main chain only)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be sent to Langfuse, but send nothing")
    ap.add_argument("--project-dir", default=DEFAULT_PROJECT_DIR,
                    help="Claude Code project transcript dir")
    ap.add_argument("--pricing", default=DEFAULT_PRICING,
                    help="path to pricing.json")
    args = ap.parse_args()

    load_dotenv(os.path.join(HERE, ".env"))
    mults, models = load_pricing(args.pricing)

    which = "latest" if args.latest or not (args.all or args.session) else "all"
    entries = find_transcripts(args.project_dir, which, args.session,
                               subagents=not args.no_subagents)

    if args.timing:
        timing_report(entries)
        return

    records = []
    for path, sid, aid in entries:
        records.extend(parse_transcript(path, sid, aid))
    if not records:
        sys.exit("No priced assistant calls found in the selected transcript(s).")

    if args.report:
        report(records, mults, models)
    else:
        export(records, mults, models, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
