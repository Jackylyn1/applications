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
#   2. rebuilds all three phase digests (preparation / cv / cover-letter)
#   3. verifies no digest lost a key it is supposed to keep
#   4. prints the token accounting
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
for p in preparation cv cover-letter; do
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

# 4. verify: every key the phase should keep is present, and each digest is
#    valid JSON. A wrong DROP entry silently removes a fact - catch it here.
"$PY" - <<'PY'
import json, sys
sys.path.insert(0, 'tools')
from profile_digest import DROP
profile = json.load(open('profile.json', encoding='utf-8'))
ok = True
for phase, dropped in DROP.items():
    path = f'.digest/profile_{phase}.json'
    d = json.load(open(path, encoding='utf-8'))
    expected = set(profile) - set(dropped)
    missing, extra = expected - set(d), set(d) - expected
    if missing or extra:
        ok = False
        print(f'  FAIL {phase}: missing={sorted(missing)} extra={sorted(extra)}')
    else:
        print(f'  ok   {phase}: {len(d)} keys, dropped {sorted(dropped) or "nothing"}')
sys.exit(0 if ok else 1)
PY

echo
"$PY" tools/profile_digest.py --stats
echo
echo "Digests rebuilt. Agents read .digest/ - never profile.json."
