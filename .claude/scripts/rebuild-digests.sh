#!/usr/bin/env bash
# rebuild-digests.sh - regenerate career-kb/.digest/ from profile.json.
#
# WHEN TO RUN
#   Every time profile.json changes. The digests are a BUILD ARTIFACT: agents
#   read them instead of profile.json, so a stale digest means agents write a
#   CV from outdated facts - silently, with no error.
#
# WHAT IT DOES
#   1. validates profile.json parses
#   2. rebuilds both phase digests (preparation / documents)
#   3. verifies no digest lost a key or sub-key it is supposed to keep, and that
#      the honesty contract survived into every phase
#   4. removes digests for phases that no longer exist, so a stale file cannot
#      be injected by a prompt that was not updated
#   5. prints the token accounting
#
# USAGE
#   .claude/scripts/rebuild-digests.sh          # rebuild + verify
#   .claude/scripts/rebuild-digests.sh --check  # verify only, exit 1 if stale
set -euo pipefail

KB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../career-kb" && pwd)"
PY="$KB/.venv/bin/python"
[ -x "$PY" ] || PY=python3
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

cd "$KB"

# 1. profile.json must be valid before anything reads it
"$PY" -c "import json,sys; json.load(open('profile.json',encoding='utf-8')); print('profile.json: valid JSON')"

# 2. staleness check - digest older than profile.json is a silent-wrong-facts bug
STALE=0
for p in preparation documents; do
  d=".digest/profile_${p}.json"
  if [ ! -f "$d" ] || [ "profile.json" -nt "$d" ]; then
    echo "STALE: $d"; STALE=1
  fi
done

if [ "$CHECK_ONLY" = "1" ]; then
  [ "$STALE" = "0" ] && { echo "all digests current"; exit 0; }
  echo "run .claude/scripts/rebuild-digests.sh to refresh" >&2; exit 1
fi

# 3. rebuild
"$PY" tools/profile_digest.py --all

# 4. verify: every key AND sub-key the phase should keep is present, each digest
#    is valid JSON, and the honesty contract survived. A wrong DROP entry
#    silently removes a fact - catch it here, not in a shipped CV.
"$PY" - <<'PY'
import json, sys
sys.path.insert(0, 'tools')
from profile_digest import DROP, DROP_FIELDS, prune_fields
profile = json.load(open('profile.json', encoding='utf-8'))
ok = True

# Never droppable, in any phase: the rules that stop a repo being claimed as
# hers when it is not. If scoping ever removes these, it is a correctness bug.
CONTRACT = [('github_repositories', 'honesty_rules'),
            ('github_repositories', 'not_own_do_not_cite')]

for phase, dropped in DROP.items():
    path = f'.digest/profile_{phase}.json'
    d = json.load(open(path, encoding='utf-8'))
    expected = set(profile) - set(dropped)
    missing, extra = expected - set(d), set(d) - expected
    problems = []
    if missing or extra:
        problems.append(f'keys missing={sorted(missing)} extra={sorted(extra)}')

    # sub-keys: what survives must equal profile.json pruned the same way
    for key, fields in DROP_FIELDS.get(phase, {}).items():
        if key not in d:
            continue
        if d[key] != prune_fields(profile[key], fields):
            problems.append(f'{key}: sub-key pruning does not match profile.json')

    for key, sub in CONTRACT:
        if key in d and sub not in d[key]:
            problems.append(f'HONESTY CONTRACT LOST: {key}.{sub}')

    if problems:
        ok = False
        for p in problems:
            print(f'  FAIL {phase}: {p}')
    else:
        subs = sum(len(f) for f in DROP_FIELDS.get(phase, {}).values())
        print(f'  ok   {phase}: {len(d)} keys, dropped '
              f'{sorted(dropped) or "nothing"} + {subs} sub-key(s)')
sys.exit(0 if ok else 1)
PY

# 5. sweep digests for phases that no longer exist. Leaving them behind means a
#    prompt that was never updated can still inject a file that looks current.
for f in .digest/profile_*.json; do
  p="$(basename "$f" .json)"; p="${p#profile_}"
  case " $(python3 -c "import sys;sys.path.insert(0,'tools');from profile_digest import DROP;print(' '.join(sorted(DROP)))") " in
    *" $p "*) ;;
    *) echo "  removing obsolete digest: $f"; rm -f "$f" ;;
  esac
done

echo
"$PY" tools/profile_digest.py --stats
echo
echo "Digests rebuilt. Agents read .digest/ - never profile.json."
