# Cross-System Integration and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Python CLI, local worker, Next.js control plane, Neon schema, and Vercel build operate together and publish accurate setup and migration documentation.

**Architecture:** Canonical contract fixtures are parsed by Python Pydantic models and TypeScript Zod schemas. A local harness then runs the real worker against the real Next.js API with fake GitHub/LLM transports. Release scripts create clean environments so repository-local imports and stale artifacts cannot hide packaging defects.

**Tech Stack:** Python 3.11+, pytest, Node.js, Next.js, Vitest, Playwright, Postgres, Vercel CLI.

---

## File Map

- Create `contracts/worker-api-v1/`: canonical JSON examples.
- Create `tests/contract/`: Python contract tests.
- Create `web/tests/contracts/`: TypeScript contract tests.
- Create `tests/e2e/`: real worker/web flow.
- Create `scripts/verify-python-release.sh`.
- Create `scripts/verify-web-release.sh`.
- Create `scripts/verify-all.sh`.
- Rewrite README and add worker/deployment/migration documentation.

### Task 1: Lock the Python/TypeScript worker contract

**Files:**
- Create: `contracts/worker-api-v1/register.json`
- Create: `contracts/worker-api-v1/claim.json`
- Create: `contracts/worker-api-v1/updates.json`
- Create: `contracts/worker-api-v1/complete.json`
- Create: `tests/contract/test_worker_api_contract.py`
- Create: `web/tests/contracts/worker-api-contract.test.ts`

- [ ] **Step 1: Write failing fixture tests**

Python:

```python
@pytest.mark.parametrize("name", ["register", "claim", "updates", "complete"])
def test_contract_fixture_parses_with_python_models(name):
    payload = json.loads((CONTRACT_DIR / f"{name}.json").read_text())
    CONTRACT_MODELS[name].model_validate(payload)
```

TypeScript:

```typescript
it.each(["register", "claim", "updates", "complete"])(
  "%s fixture parses with the web schema",
  async (name) => {
    const payload = await readContract(name);
    expect(CONTRACT_SCHEMAS[name].safeParse(payload).success).toBe(true);
  },
);
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/contract/test_worker_api_contract.py -q
cd web && npm test -- --run tests/contracts/worker-api-contract.test.ts
```

- [ ] **Step 3: Add canonical version-1 fixtures**

Every fixture includes `schemaVersion: 1`. Use camelCase on the wire and Pydantic aliases. Align status enums, progress counters, provider specs, dictionary/output-root names, errors, and completion summaries exactly.

- [ ] **Step 4: Verify GREEN**

Run both contract commands again and confirm every fixture parses on both sides.

- [ ] **Step 5: Commit**

```bash
git add contracts tests/contract web/tests/contracts src/gitbook_translator/worker/models.py web/lib/schemas
git commit -m "test: lock worker api version one contract"
```

### Task 2: Run a real local worker against the real control plane

**Files:**
- Create: `tests/e2e/test_worker_web_flow.py`
- Create: `tests/e2e/fake_services.py`
- Create: `web/tests/fixtures/seed-worker.ts`
- Create: `scripts/run-local-stack.sh`

- [ ] **Step 1: Write the failing system test**

Launch a test Postgres database and Next.js server, start the Python worker with fake GitHub/OpenAI/Gemini/Ollama transports, create a job through the admin API, and assert:

```python
assert final_job["state"] == "succeeded"
assert final_job["resultSummary"]["successCount"] == 1
assert Path(local_output, "README.en.md").read_text() == EXPECTED_TRANSLATION
```

Add a cancellation scenario that stops after the first progress event and verifies no later-language output exists.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/e2e/test_worker_web_flow.py -q
```

- [ ] **Step 3: Add the local-stack harness**

The harness exports isolated ports and test secrets, applies migrations, starts `next start`, and cleans child processes on exit. Adjust only contract or lifecycle defects exposed by the test; do not mock the worker/control-plane HTTP boundary.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/e2e/test_worker_web_flow.py -q
```

- [ ] **Step 5: Commit**

```bash
git add tests/e2e web/tests/fixtures scripts/run-local-stack.sh
git commit -m "test: verify worker and web integration"
```

### Task 3: Rewrite user, worker, and deployment documentation

**Files:**
- Rewrite: `README.md`
- Create: `docs/worker-setup.md`
- Create: `docs/web-deployment.md`
- Create: `docs/migration-from-glossary.md`
- Modify: `.env.example`
- Modify: `web/.env.example`
- Test: `tests/docs/test_documentation.py`

- [ ] **Step 1: Write failing documentation assertions**

```python
def test_documentation_matches_supported_features():
    assert "--dictionary-path" in README
    assert "--glossary-path" not in README
    assert "gitbook-translator worker" in WORKER_DOCS
    assert "dictionary_zh-cn.json" in MIGRATION_DOCS
    assert "Vercel Blob" not in DEPLOYMENT_DOCS
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/docs/test_documentation.py -q
```

- [ ] **Step 3: Rewrite documentation**

Document fresh installation; CLI examples for OpenAI, Gemini, and Ollama; dictionary layout; cache and exit codes; worker TOML, secrets, and local output semantics; Neon provisioning and migrations; password hash generation; Vercel variables; the local Ollama security boundary; and legacy glossary/cache migration.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/docs/test_documentation.py -q
```

- [ ] **Step 5: Commit**

```bash
git add README.md docs .env.example web/.env.example tests/docs
git commit -m "docs: document cli worker and vercel deployment"
```

### Task 4: Add reproducible release verification scripts

**Files:**
- Create: `scripts/verify-python-release.sh`
- Create: `scripts/verify-web-release.sh`
- Create: `scripts/verify-all.sh`
- Modify: `pyproject.toml`
- Modify: `web/package.json`
- Test: `tests/integration/test_release_scripts.py`

- [ ] **Step 1: Write a failing release-script smoke test**

Assert every script exists, is executable, contains `set -euo pipefail`, and invokes the expected full test/build commands.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/integration/test_release_scripts.py -q
```

- [ ] **Step 3: Implement release scripts**

`verify-python-release.sh` creates a temporary environment, installs tests, runs all Python tests, builds a wheel, installs it into a second environment, changes to `/tmp`, and runs CLI/worker help.

`verify-web-release.sh` runs migration tests, lint, type-check, Vitest, production build, and Playwright with explicit test database variables.

`verify-all.sh` calls both and then `git diff --check`.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/integration/test_release_scripts.py -q
```

- [ ] **Step 5: Commit**

```bash
git add scripts pyproject.toml web/package.json tests/integration/test_release_scripts.py
git commit -m "build: add reproducible release verification"
```

### Task 5: Perform the final release and Vercel readiness gate

**Files:**
- Modify only files required by failures found during this gate.

- [ ] **Step 1: Verify the full Python release**

```bash
./scripts/verify-python-release.sh
```

Expected: every Python test passes; wheel builds; installed CLI and worker help exit `0` outside the repository.

- [ ] **Step 2: Verify migration and web release**

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" ./scripts/verify-web-release.sh
```

Expected: migrations, lint, type-check, tests, production build, and E2E pass.

- [ ] **Step 3: Verify the cross-system flow**

```bash
pytest tests/e2e/test_worker_web_flow.py -q
```

Expected: success and cancellation scenarios pass.

- [ ] **Step 4: Verify Vercel configuration**

```bash
cd web
vercel build
```

Expected: Vercel build succeeds with no translation runtime in server functions and no secret values printed.

- [ ] **Step 5: Inspect state and commit release fixes**

```bash
git diff --check
git status --short
```

If verification required fixes:

```bash
git add -A
git commit -m "fix: complete translation platform release verification"
```

Do not claim completion until all four verification commands above have fresh successful output.
