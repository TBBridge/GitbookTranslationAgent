#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/verify-python-release.sh"
"$ROOT/scripts/verify-web-release.sh"

cd "$ROOT"
git diff --check
