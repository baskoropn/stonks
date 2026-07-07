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

if [[ "${1:-}" != "-h" && "${1:-}" != "--help" ]]; then
  echo "Started: $START_TIME"
  mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/data/reports"
  find "$ROOT_DIR/data/raw" -mindepth 1 -delete
  find "$ROOT_DIR/data/reports" -mindepth 1 -delete
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/download_ihsg_2026.py" "$@"

if [[ "${1:-}" != "-h" && "${1:-}" != "--help" ]]; then
  END_EPOCH="$(date +%s)"
  END_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
  ELAPSED_SECONDS=$((END_EPOCH - START_EPOCH))
  printf 'Finished: %s\n' "$END_TIME"
  printf 'Elapsed: %02d:%02d:%02d\n' \
    $((ELAPSED_SECONDS / 3600)) \
    $(((ELAPSED_SECONDS % 3600) / 60)) \
    $((ELAPSED_SECONDS % 60))
fi
