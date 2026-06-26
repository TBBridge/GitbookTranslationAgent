# GitBook Translation Agent

Deterministic GitBook/Markdown translation tooling with two entry points:

- `gitbook-translator translate` for direct CLI runs.
- `gitbook-translator worker` for local execution of jobs created in the Vercel web control plane.

The translator preserves Markdown structure, protected spans, links, code blocks, and GitBook syntax while using language-specific dictionaries from `dictionary_*.json` files.

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
