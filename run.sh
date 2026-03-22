#!/usr/bin/env bash
# run.sh — thin wrapper that delegates to run.py (cross-platform runner)
# Works on Linux, macOS, and Windows (Git Bash / MSYS2 / WSL)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find a Python interpreter
for cmd in python3 python py; do
  if command -v "$cmd" >/dev/null 2>&1; then
    exec "$cmd" "$ROOT_DIR/run.py" "$@"
  fi
done

echo "ERROR: python not found. Install Python 3.8+ and try again."
exit 1
