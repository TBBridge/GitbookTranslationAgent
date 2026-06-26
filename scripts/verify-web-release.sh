#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/web"

npm test -- --run tests/db/migrations.test.ts
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run test:e2e
