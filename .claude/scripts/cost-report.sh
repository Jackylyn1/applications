#!/usr/bin/env bash
# cost-report.sh - what did that task cost, in tokens, dollars and time.
#
# WHY THIS EXISTS
#   Asking Claude "what did that cost?" loads a pricing skill into the session
#   prefix, which is then re-read on every later call - measuring the cost
#   costs more than the run being measured. This reads the numbers instead.
#
# WHAT IT DOES
#   Ingests any new Claude Code transcripts into observability/costs.db
#   (idempotent, keyed on message id) and prints one table:
#
#     task | model | calls | time | fresh in | cache rd | cache wr | output |
#     tokens | cost | %
#
#   All parsing, pricing and SQL live in observability/cc_costs.py - this is
#   only the ingest-then-report wrapper. Every flag is passed straight through.
#
# USAGE
#   cost-report.sh                                   # newest session, per step
#   cost-report.sh --command generate-application    # its LAST run, per step
#   cost-report.sh --command generate-application --by turn
#   cost-report.sh --command generate-application --runs --by command
#   cost-report.sh --command generate-application --runs --like Company B --by run
#   cost-report.sh --session <id>                    # one terminal's session
#   cost-report.sh --agent <id> --by call            # inside one subagent
#   cost-report.sh --all --by command                # cost per command, ever
#   cost-report.sh --all --by model                  # cost per model
#   cost-report.sh --today --by turn                 # today, prompt by prompt
#
#   --by step|turn|run|command|agent|model|session|call   row granularity
#   --like TEXT        keep whole runs mentioning TEXT (an employer, a file)
#   --sort cost|time|tokens|calls|ts   --limit N   --exact   --json
#   --no-ingest        skip the transcript scan (pure DB read)
#   -h, --help         this text, then the full report help
#
# ACCURACY
#   Tokens are exact (from the transcripts the API wrote). Cost is derived from
#   observability/pricing.json. Time is derived from timestamps: "time" is
#   model generation time, which excludes tool execution and human think time -
#   so it is well below the wall span printed underneath the table.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$HERE/../.." && pwd)}"
CC_COSTS="$PROJECT_DIR/observability/cc_costs.py"

[ -f "$CC_COSTS" ] || { echo "missing $CC_COSTS" >&2; exit 1; }

INGEST=1
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-ingest) INGEST=0 ;;
    -h|--help)   # the header comment, then the report's own flag reference
      awk 'NR > 1 { if (!/^#/) exit; sub(/^# ?/, ""); print }' "$0"
      python3 "$CC_COSTS" report --help
      exit 0 ;;
    *) ARGS+=("$arg") ;;
  esac
done

# Scopes that can reach beyond the newest session need every transcript.
SCAN=--latest
for arg in ${ARGS[@]+"${ARGS[@]}"}; do
  case "$arg" in
    --all|--today|--command*|--session*|--agent*|--turn*|--since*) SCAN=--all; break ;;
  esac
done

if [ "$INGEST" = 1 ]; then
  python3 "$CC_COSTS" ingest "$SCAN" >/dev/null
fi

exec python3 "$CC_COSTS" report ${ARGS[@]+"${ARGS[@]}"}
