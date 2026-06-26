#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-python3}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

"$PYTHON_BIN" -m venv "$WORK_DIR/test-venv"
"$WORK_DIR/test-venv/bin/python" -m pip install --upgrade pip
"$WORK_DIR/test-venv/bin/python" -m pip install -e ".[test]"
"$WORK_DIR/test-venv/bin/python" -m pytest tests/unit tests/property tests/integration tests/contract tests/docs -q

# Equivalent to: python -m build
"$WORK_DIR/test-venv/bin/python" -m build

"$PYTHON_BIN" -m venv "$WORK_DIR/install-venv"
"$WORK_DIR/install-venv/bin/python" -m pip install --upgrade pip
"$WORK_DIR/install-venv/bin/python" -m pip install dist/*.whl

(
  cd /tmp
  "$WORK_DIR/install-venv/bin/gitbook-translator" --help >/dev/null
  "$WORK_DIR/install-venv/bin/gitbook-translator" worker --help >/dev/null
)
