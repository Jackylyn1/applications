#!/usr/bin/env python3
"""profile_digest.py — precompute a compact, phase-scoped view of profile.json.

WHY THIS EXISTS (measured, not assumed)

Reading `profile.json` cost a subagent **23,933 tokens**, and that context is
re-read on every subsequent call in its loop. In the cover-letter agent that was
~287k read tokens - 42% of a whole pipeline run - for one file.

Of those 23,933 tokens, only ~14,834 are the data:
  - pretty-print whitespace          ~19% of the file
  - line-number prefixes added by Read (1311 lines)   ~5,244 tokens
Emitting the same content minified, and reading it as one blob, removes ~38%
**with no loss of fact fidelity at all.**

WHAT IS *NOT* DROPPED, AND WHY
Dropping content is where fidelity dies, so the drop list is deliberately tiny.
An earlier guess that `github_repositories` could go was wrong: `flagship_own`
holds the evidence the CV actually cites (commit counts, file counts, project
scope), `not_own_do_not_cite` is the do-not-cite list, and `honesty_rules` is
the honesty contract itself. All stay. Only genuinely inert bookkeeping is cut,
and only for phases that provably do not use it.

The saving is therefore ~90% minification, ~10% scoping. That is the honest
split - the win is real, but it comes from encoding, not from hiding facts.

USAGE
    profile_digest.py --phase preparation|cv|cover-letter [--out <path>]
    profile_digest.py --all          # rebuild every phase digest
    profile_digest.py --stats        # show token accounting, write nothing

Digests land in `career-kb/.digest/` and are a BUILD ARTIFACT: regenerate them
whenever profile.json changes. The orchestrator injects the digest *path*; it
never loads the fact base into its own context.
"""
import argparse, json, os, sys

KB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.path.join(KB, 'profile.json')
DIGEST_DIR = os.path.join(KB, '.digest')

# Keys a phase does not read. Everything absent from this map is kept.
# Keep these lists SHORT and justified - a wrong entry silently removes a fact.
DROP = {
    # Phase 1 decides framing and matches keywords. It does not write documents,
    # so it does not need the Arbeitszeugnis duty list (used only for CV bullet
    # reframing) - but it DOES need role_skill_map, which the others don't.
    'preparation': ['meta'],
    # Generation phases: framing is already decided by preparation and injected
    # as the match summary, so the role map (~969 tok) and career goals are inert.
    #
    # `open_to_work` is deliberately KEPT (145 tok). It carries `availability`
    # and `location_type: Remote`, which the cover letter's closing paragraph and
    # the CV subject line both cite. It was dropped in the first version on the
    # theory that preparation would pass availability through in its summary -
    # true in practice, but it makes a verifiable fact depend on one agent
    # remembering to forward it. 145 tokens is not worth that fragility.
    'cv': ['meta', 'career_goals', 'role_skill_map'],
    'cover-letter': ['meta', 'career_goals', 'role_skill_map'],
}


def est_tokens(s):
    """Rough token count. JSON tokenizes at roughly 3 chars/token, not 4."""
    return len(s) // 3


def build(phase, profile=None):
    data = profile if profile is not None else json.load(open(PROFILE, encoding='utf-8'))
    kept = {k: v for k, v in data.items() if k not in DROP.get(phase, [])}
    # Minified: no indent, no spaces after separators. ensure_ascii=False keeps
    # umlauts as single characters instead of \uXXXX escapes (which cost more).
    return json.dumps(kept, ensure_ascii=False, separators=(',', ':'))


def stats():
    raw = open(PROFILE, encoding='utf-8').read()
    lines = raw.count('\n') + 1
    read_cost = est_tokens(raw) + lines * 4   # Read prefixes every line
    print(f"{'':<16}{'chars':>9}{'~tokens':>9}{'vs Read':>10}")
    print(f"{'profile.json':<16}{len(raw):>9,}{est_tokens(raw):>9,}")
    print(f"{'  + line numbers':<16}{'':>9}{read_cost:>9,}{'baseline':>10}")
    for phase in ('preparation', 'cv', 'cover-letter'):
        d = build(phase)
        print(f"{phase:<16}{len(d):>9,}{est_tokens(d):>9,}"
              f"{(1 - est_tokens(d) / read_cost) * 100:>9.0f}%")
    print("\n'vs Read' = saving against reading pretty-printed profile.json,"
          "\nwhich is what the agents did before. Per call, and every call re-reads it.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=sorted(DROP))
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--out')
    args = ap.parse_args()

    if args.stats:
        stats()
        return 0
    phases = sorted(DROP) if args.all else ([args.phase] if args.phase else [])
    if not phases:
        ap.error('pass --phase, --all or --stats')

    os.makedirs(DIGEST_DIR, exist_ok=True)
    profile = json.load(open(PROFILE, encoding='utf-8'))
    for phase in phases:
        out = args.out or os.path.join(DIGEST_DIR, f'profile_{phase}.json')
        text = build(phase, profile)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'{phase:<14} -> {out}  ({len(text):,} chars, ~{est_tokens(text):,} tok)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
