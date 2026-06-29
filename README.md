# GitBook Translation Platform

Deterministic GitBook/Markdown translation tooling with two entry points:

- `gitbook-translator translate` for direct CLI runs.
- `gitbook-translator worker` for local execution of jobs created in the Vercel web control plane.

The translator preserves Markdown structure, protected spans, links, code blocks, and GitBook syntax while using language-specific dictionaries from `dictionary_*.json` files.

> **Note:** This project replaced its original LangChain ReAct agent with a
> deterministic pipeline. Translation no longer relies on an LLM to orchestrate
> the workflow; the LLM is called only for the translation, review, and
> correction steps inside a fixed, auditable control flow.

## Architecture

The platform has three parts that communicate only through a single
**versioned job schema** — the web app never runs translation itself.

```text
                 create / monitor jobs
   Administrator ───────────────────────▶  ┌────────────────────────────┐
   (browser)                                │  Web control plane (web/)  │
                                            │  Next.js on Vercel         │
                                            │  + Neon Postgres           │
                                            │  queues jobs, leases work  │
                                            └─────────────┬──────────────┘
                                       lease / heartbeat / │ progress (HTTP, bearer token)
                                       complete            ▼
                                            ┌────────────────────────────┐
   Local machine / on-prem  ──────────────▶│  Local worker              │
   (Ollama, file output, GitHub token)     │  src/gitbook_translator/   │
                                            │      worker/               │
                                            └─────────────┬──────────────┘
                                                          │ invokes
                                                          ▼
                                            ┌────────────────────────────┐
                                            │  Deterministic pipeline    │
                                            │  src/gitbook_translator/   │
                                            │  validate→fetch→dictionary │
                                            │  →translate→verify→save    │
                                            └────────────────────────────┘
```

- **Python core** (`src/gitbook_translator/`): the deterministic pipeline,
  markdown segment preservation, mechanical verification, fingerprint cache, and
  lazy OpenAI/Gemini/Ollama provider adapters. Runnable standalone via the
  `translate` CLI — no web app required.
- **Local worker** (`src/gitbook_translator/worker/`): leases jobs from the
  control plane and runs the pipeline locally, keeping long-running work and
  local resources (Ollama, output files) off the serverless platform.
- **Web control plane** (`web/`): a Next.js App Router app on Vercel backed by
  Neon Postgres. It authenticates administrators and workers, queues jobs, and
  safely leases them to workers; it does not perform translation.

## Requirements

- Python 3.11+
- Node.js 20.9+ for the `web/` control plane
- A GitHub token for private repositories
- One translation provider:
  - Ollama for local LLM execution
  - OpenAI
  - Google Gemini

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

For the web app:

```bash
cd web
npm install
```

## Dictionary layout

Use a directory containing one JSON file per target language:

```text
dictionaries/default/
  dictionary_en.json
  dictionary_zh-cn.json
  dictionary_zh-tw.json
```

Each file is a flat object:

```json
{
  "帳票定義": "Template Form",
  "ワークフロー": "Workflow"
}
```

## CLI examples

Local Ollama:

```bash
gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --branch main \
  --target-paths "docs/**/*.md" README.md \
  --languages en zh-CN \
  --dictionary-path ./dictionaries/default \
  --output-root ./output \
  --provider ollama \
  --model qwen3 \
  --provider-base-url http://127.0.0.1:11434
```

OpenAI:

```bash
OPENAI_API_KEY=... gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --target-paths "docs/**/*.md" \
  --languages en \
  --dictionary-path ./dictionaries/default \
  --provider openai \
  --model gpt-4.1-mini
```

Gemini:

```bash
GOOGLE_API_KEY=... gitbook-translator translate \
  --repo-url https://github.com/acme/docs \
  --target-paths "docs/**/*.md" \
  --languages zh-CN \
  --dictionary-path ./dictionaries/default \
  --provider gemini \
  --model gemini-2.5-flash
```

Exit codes:

- `0`: succeeded
- `1`: failed
- `2`: partial or cancelled
- `130`: interrupted

## Local worker

The worker keeps long-running translation work on your machine while Vercel hosts only the control plane:

```bash
WORKER_TOKEN=... gitbook-translator worker --config worker.example.toml
```

Use `--once` for diagnostics:

```bash
gitbook-translator worker --config worker.example.toml --once
```

See [docs/worker-setup.md](docs/worker-setup.md).

## Web control plane

The `web/` application is a Next.js App Router app for Vercel. It stores jobs, workers, sessions, leases, and logs in Neon Postgres.

```bash
cd web
npm run typecheck
npm run test:run
npm run build
npm run test:e2e
```

See [docs/web-deployment.md](docs/web-deployment.md).

## Verification

```bash
.venv/bin/python -m pytest tests/unit tests/property tests/integration tests/contract -q
cd web && npm run lint && npm run typecheck && npm run test:run && npm run build
```

The web database migration test and the Playwright E2E suite require a real
Postgres instance via `TEST_DATABASE_URL`; the Python cross-system E2E
(`tests/e2e/`) runs against the real web API using an in-memory store
(`E2E_IN_MEMORY=1`) and needs `web/` dependencies installed.

## Repository layout

```text
src/gitbook_translator/   Python core pipeline, providers, and local worker
dictionaries/default/     Language-specific dictionaries (dictionary_<lang>.json)
web/                      Next.js + Neon control plane (Vercel)
contracts/                Shared worker API contract fixtures
tests/                    unit / property / integration / contract / e2e suites
docs/                     Setup, deployment, and design documentation
```

## Documentation

- [docs/worker-setup.md](docs/worker-setup.md) — configure and run the local worker.
- [docs/web-deployment.md](docs/web-deployment.md) — deploy the control plane on Vercel + Neon.
- [docs/migration-from-glossary.md](docs/migration-from-glossary.md) — migrate legacy glossaries to dictionaries.
