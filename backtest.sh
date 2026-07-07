#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
START_EPOCH="$(date +%s)"
START_TIME="$(date '+%Y-%m-%d %H:%M:%S')"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at: $PYTHON_BIN" >&2
  exit 1
fi

usage() {
  cat <<'EOF'
Usage:
  bash backtest.sh --swing [backtest options]
  bash backtest.sh --macd [backtest options]
  bash backtest.sh --all [backtest options]

Options:
  --swing   Backtest swing_candidate.
  --macd    Backtest macd_candidate.
  --all     Backtest all screeners.
  -h, --help

Backtest options after the screener flag are passed to scripts/backtest.py.
Example:
  bash backtest.sh --swing --hold-days 3
EOF
}

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  --swing|--macd|--all)
    MODE="$1"
    shift
    ;;
  *)
    echo "Unknown option: $1" >&2
    usage >&2
    exit 2
    ;;
esac

run_swing() {
  "$PYTHON_BIN" "$ROOT_DIR/scripts/backtest.py" \
    --input-pattern "ihsg_swing_indicators_*.csv" \
    --signal-column swing_candidate \
    --strategy-name swing \
    "$@"
}

run_macd() {
  "$PYTHON_BIN" "$ROOT_DIR/scripts/backtest.py" \
    --input-pattern "ihsg_macd_indicators_*.csv" \
    --signal-column macd_candidate \
    --strategy-name macd \
    "$@"
}

echo "Started: $START_TIME"

case "$MODE" in
  --swing)
    run_swing "$@"
    ;;
  --macd)
    run_macd "$@"
    ;;
  --all)
    run_swing "$@"
    run_macd "$@"
    ;;
esac

END_EPOCH="$(date +%s)"
END_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
ELAPSED_SECONDS=$((END_EPOCH - START_EPOCH))
printf 'Finished: %s\n' "$END_TIME"
printf 'Elapsed: %02d:%02d:%02d\n' \
  $((ELAPSED_SECONDS / 3600)) \
  $(((ELAPSED_SECONDS % 3600) / 60)) \
  $((ELAPSED_SECONDS % 60))
