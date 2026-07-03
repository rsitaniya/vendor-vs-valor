#!/usr/bin/env bash
# Full pipeline run — reads need from input-market-data-india.md (or $1) and drives end-to-end.
# Usage: ./run.sh [path/to/input-market-data-india.md]
set -euo pipefail

INPUT="${1:-input-market-data-india.md}"

if [ ! -f "$INPUT" ]; then
  echo "ERROR: input file not found: $INPUT" >&2
  exit 2
fi

echo "==> running vendor-vs-valor pipeline with input: $INPUT"
uv run python run.py "$INPUT"
