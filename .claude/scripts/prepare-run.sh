#!/usr/bin/env bash
# prepare-run.sh - everything /generate-application needs before phase 1.
#
# WHY THIS EXISTS
#   The orchestrator used to open a run with two separate shell calls: rebuild
#   the digests, then list content/ for the base-JSON inventory. Each Bash call
#   is a full turn - the whole conversation is re-sent, the model waits, and the
#   result comes back - to move a few hundred bytes. The work itself is under a
#   second. Collapsing them removes a round-trip from every single run.
#
#   Path resolution stays separate (render_application.py --print-paths), and
#   has to: it needs the company slug, which does not exist until preparation
#   has read the offer.
#
# WHAT IT PRINTS
#   1. digest rebuild + verification (delegated to rebuild-digests.sh, so the
#      key/sub-key checks live in exactly one place)
#   2. the digest paths to inject
#   3. the base content JSON inventory preparation chooses from
#
# USAGE
#   .claude/scripts/prepare-run.sh            # rebuild + report
#   .claude/scripts/prepare-run.sh --check    # verify only, exit 1 if stale
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KB="$(cd "$HERE/../../career-kb" && pwd)"

"$HERE/rebuild-digests.sh" "$@"

# --check is a verification-only mode; nothing below applies.
[ "${1:-}" = "--check" ] && exit 0

echo
echo "DIGESTS TO INJECT"
for d in "$KB"/.digest/profile_*.json; do
  echo "  $d"
done

echo
echo "BASE CONTENT JSON INVENTORY (preparation picks exactly one)"
# Only the role bases are selectable. offer_*/patch_* are per-application build
# artifacts from previous runs - naming one as a base would tailor a new
# application on top of an old company's edits.
find "$KB/content" -maxdepth 1 -name '*.json' \
     ! -name 'offer_*' ! -name 'patch_*' -printf '  %p\n' | sort
