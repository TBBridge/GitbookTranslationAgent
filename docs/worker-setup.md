# Local worker setup

The local worker polls the Vercel control plane, leases one job at a time, runs the Python translation pipeline locally, and reports progress back to the web app.

## Configure

Copy the example:

```bash
cp worker.example.toml worker.toml
```

Set a secret in your shell or `.env.local` equivalent:

```bash
export WORKER_TOKEN="$(openssl rand -hex 32)"
```

Use the same value as `WORKER_TOKEN` in Vercel.

## Run

```bash
gitbook-translator worker --config worker.toml
```

Run one polling cycle:

```bash
gitbook-translator worker --config worker.toml --once
```

The worker advertises dictionary set names, output root names, provider names, models, and languages. It never sends local filesystem paths or provider secrets to the control plane.

## Ollama boundary

Ollama runs on your local machine. Keep `base_url` pointed at a trusted local endpoint such as `http://127.0.0.1:11434`; do not expose Ollama publicly without separate network authentication.

## Output semantics

The web app records job state and returned local output paths. Files remain on the worker machine under the configured output root.
