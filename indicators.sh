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
  bash indicators.sh --swing
  bash indicators.sh --macd
  bash indicators.sh --all

Options:
  --swing   Build swing screener indicators and reports.
  --macd    Build MACD screener indicators and reports.
  --all     Build all indicator reports.
EOF
}

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 2
fi

case "${1:-}" in
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

if [[ $# -ne 0 ]]; then
  echo "Unexpected parameter: $1" >&2
  usage >&2
  exit 2
fi

echo "Started: $START_TIME"

case "$MODE" in
  --swing)
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build_swing_indicators.py"
    ;;
  --macd)
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build_macd_indicators.py"
    ;;
  --all)
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build_swing_indicators.py"
    "$PYTHON_BIN" "$ROOT_DIR/scripts/build_macd_indicators.py"
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
