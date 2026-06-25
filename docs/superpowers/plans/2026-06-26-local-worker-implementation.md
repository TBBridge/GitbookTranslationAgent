# Local Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reliable local worker that advertises local capabilities, exclusively leases web-created jobs, executes the shared pipeline, reports progress, and handles cancellation and lease recovery.

**Architecture:** The worker is a thin adapter around the Python translation core. A typed HTTP client owns the versioned control-plane contract, while a worker runner owns polling, lease renewal, cancellation, local outbox persistence, and pipeline invocation.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, pytest, pytest-httpx.

---

## File Map

- Create `src/gitbook_translator/worker/models.py`: API payloads and local configuration.
- Create `src/gitbook_translator/worker/config.py`: TOML loading and capability discovery.
- Create `src/gitbook_translator/worker/client.py`: authenticated control-plane client.
- Create `src/gitbook_translator/worker/outbox.py`: durable pending updates.
- Create `src/gitbook_translator/worker/runner.py`: polling and lease lifecycle.
- Modify `src/gitbook_translator/cli.py`: `worker` subcommand.

### Task 1: Define worker configuration and capability discovery

**Files:**
- Create: `src/gitbook_translator/worker/__init__.py`
- Create: `src/gitbook_translator/worker/models.py`
- Create: `src/gitbook_translator/worker/config.py`
- Test: `tests/unit/worker/test_config.py`

- [ ] **Step 1: Write failing configuration tests**

```python
def test_worker_discovers_dictionary_languages(tmp_path):
    root = tmp_path / "dictionaries" / "default"
    root.mkdir(parents=True)
    (root / "dictionary_en.json").write_text('{"翻訳":"Translation"}')
    config = load_worker_config(worker_toml(tmp_path))
    assert config.capabilities.dictionary_sets["default"].languages == ["en"]


def test_worker_rejects_output_root_name_with_escape(tmp_path):
    with pytest.raises(ValueError):
        parse_worker_config({"output_roots": {"../bad": str(tmp_path)}})
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/worker/test_config.py -q
```

- [ ] **Step 3: Implement TOML configuration**

Use `tomllib`. Define `WorkerConfig` with server URL, worker name, token environment variable, poll/heartbeat/lease intervals, named dictionary sets, named output roots, and provider/model declarations. Resolve all local paths on startup. Capability payloads expose names and supported languages, never physical paths or secrets.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/worker/test_config.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/worker tests/unit/worker/test_config.py
git commit -m "feat: add local worker configuration"
```

### Task 2: Implement the versioned worker API client

**Files:**
- Create: `src/gitbook_translator/worker/client.py`
- Create: `tests/fixtures/worker_contract/register-success.json`
- Create: `tests/fixtures/worker_contract/claim-success.json`
- Create: `tests/fixtures/worker_contract/complete-success.json`
- Test: `tests/unit/worker/test_client.py`

- [ ] **Step 1: Write failing client tests**

```python
def test_register_sends_bearer_token(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/register",
        json={"workerId": "w1"},
    )
    worker_client.register(CAPABILITIES)
    assert httpx_mock.get_request().headers["Authorization"] == "Bearer worker-secret"


def test_claim_parses_versioned_job(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/claim",
        json=json_fixture("claim-success.json"),
    )
    assert worker_client.claim().job.config.schema_version == 1
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/worker/test_client.py -q
```

- [ ] **Step 3: Implement explicit API methods**

Implement `register`, `heartbeat`, `claim`, `renew`, `send_updates`, `cancellation_state`, and `complete`. Every request has a timeout, bearer header, worker version, and idempotency key where applicable. Parse responses through Pydantic aliases and redact response bodies from authentication failures.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/worker/test_client.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/worker/client.py tests/unit/worker/test_client.py tests/fixtures/worker_contract
git commit -m "feat: add worker control-plane client"
```

### Task 3: Add a durable progress outbox

**Files:**
- Create: `src/gitbook_translator/worker/outbox.py`
- Test: `tests/unit/worker/test_outbox.py`

- [ ] **Step 1: Write failing persistence tests**

```python
def test_unsent_events_survive_restart(tmp_path):
    path = tmp_path / "outbox.jsonl"
    Outbox(path).append(progress_event(sequence=1))
    assert Outbox(path).pending()[0].sequence == 1


def test_outbox_redacts_secrets(tmp_path):
    outbox = Outbox(tmp_path / "outbox.jsonl")
    outbox.append(log_event("Authorization: Bearer abc123"))
    assert "abc123" not in outbox.path.read_text()
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/worker/test_outbox.py -q
```

- [ ] **Step 3: Implement append-only delivery state**

Write sanitized JSON lines with monotonic sequence numbers. Track the last acknowledged sequence in a state file written atomically. Compact acknowledged entries after successful batches. Never persist job credentials, cookies, authorization headers, or provider secrets.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/worker/test_outbox.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/worker/outbox.py tests/unit/worker/test_outbox.py
git commit -m "feat: persist worker progress delivery"
```

### Task 4: Implement polling, leases, cancellation, and pipeline execution

**Files:**
- Create: `src/gitbook_translator/worker/runner.py`
- Test: `tests/unit/worker/test_runner.py`
- Test: `tests/integration/test_worker_lifecycle.py`

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_runner_renews_lease_during_long_job(fake_client, fake_pipeline, clock):
    fake_client.claim_result = CLAIM
    fake_pipeline.advance_clock(clock, seconds=40)
    runner = WorkerRunner(
        client=fake_client,
        pipeline=fake_pipeline,
        config=WORKER_CONFIG,
        outbox=MemoryOutbox(),
        clock=clock,
        sleeper=lambda _: None,
    )
    runner.run_once()
    assert fake_client.renew_calls >= 2


def test_cancel_request_stops_between_languages(fake_client, fake_pipeline):
    fake_client.cancel_after_progress(sequence=3)
    runner = WorkerRunner(
        client=fake_client,
        pipeline=fake_pipeline,
        config=WORKER_CONFIG,
        outbox=MemoryOutbox(),
        clock=FakeClock(),
        sleeper=lambda _: None,
    )
    result = runner.run_once()
    assert result.status == RunStatus.CANCELLED
    assert fake_pipeline.languages_started == ["en"]
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/worker/test_runner.py tests/integration/test_worker_lifecycle.py -q
```

- [ ] **Step 3: Implement worker lifecycle**

`run_once()` registers or heartbeats if due, flushes the outbox, claims one job, maps capability names to local paths/providers, starts lease renewal, invokes the pipeline, batches events, checks cancellation through the pipeline probe, sends completion, and stops renewal in `finally`. A lost lease stops processing at the next cancellation boundary and sends no unowned completion.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/worker/test_runner.py tests/integration/test_worker_lifecycle.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/worker/runner.py tests/unit/worker/test_runner.py tests/integration/test_worker_lifecycle.py
git commit -m "feat: execute leased translation jobs locally"
```

### Task 5: Expose the worker command and verify process behavior

**Files:**
- Modify: `src/gitbook_translator/cli.py`
- Create: `worker.example.toml`
- Modify: `.env.example`
- Test: `tests/integration/test_worker_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_worker_help_lists_config_option():
    result = subprocess.run(
        [sys.executable, "-m", "gitbook_translator.cli", "worker", "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "--config" in result.stdout


def test_worker_sigint_returns_130(monkeypatch):
    monkeypatch.setattr(WorkerRunner, "run_forever", Mock(side_effect=KeyboardInterrupt))
    assert cli.main(["worker", "--config", "worker.example.toml"]) == 130
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/integration/test_worker_cli.py -q
```

- [ ] **Step 3: Implement CLI wiring**

Add `worker --config PATH [--once]`. Resolve `WORKER_TOKEN` from the configured environment variable. `--once` performs one polling cycle for diagnostics and service managers. Keep secrets out of `worker.example.toml`.

- [ ] **Step 4: Run the worker phase suite**

```bash
pytest tests/unit/worker tests/integration/test_worker_lifecycle.py tests/integration/test_worker_cli.py -q
python -m gitbook_translator.cli worker --help
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/cli.py worker.example.toml .env.example tests/integration/test_worker_cli.py
git commit -m "feat: expose local translation worker command"
```
