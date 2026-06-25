# Python Translation Core and CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ReAct agent with a deterministic, installable Python translation pipeline and repair all audited CLI, dictionary, cache, path, GitHub, and formatting defects.

**Architecture:** Create a real `gitbook_translator` package under `src/` with typed models and dependency-injected ports. The pipeline coordinates concrete components in ordinary Python control flow; provider SDKs are lazy adapters behind one protocol, allowing tests and CLI help to run without API keys.

**Tech Stack:** Python 3.11+, setuptools, Pydantic 2, httpx, PyGithub, OpenAI SDK, Google Gen AI SDK, pytest, Hypothesis.

---

## File Map

- Create `src/gitbook_translator/models.py`: requests, events, issues, and results.
- Create `src/gitbook_translator/config.py`: validation and normalization.
- Create `src/gitbook_translator/paths.py`: containment-safe paths.
- Create `src/gitbook_translator/dictionaries.py`: dictionary loading and hashing.
- Create `src/gitbook_translator/markdown.py`: stable segments and reconstruction.
- Create `src/gitbook_translator/verification.py`: mechanical checks.
- Create `src/gitbook_translator/cache.py`: atomic fingerprint cache.
- Create `src/gitbook_translator/providers/`: provider protocol and adapters.
- Create `src/gitbook_translator/github_client.py`: explicit fetch and push results.
- Create `src/gitbook_translator/pipeline.py`: deterministic orchestration.
- Create `src/gitbook_translator/cli.py`: CLI and exit-code mapping.
- Replace legacy tests with focused tests under `tests/unit/`, `tests/property/`, and `tests/integration/`.

### Task 1: Establish the installable package and typed result contract

**Files:**
- Create: `src/gitbook_translator/__init__.py`
- Create: `src/gitbook_translator/models.py`
- Create: `src/gitbook_translator/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_models.py`
- Test: `tests/integration/test_package_entrypoint.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_status_derives_exit_code():
    assert RunStatus.SUCCEEDED.exit_code == 0
    assert RunStatus.FAILED.exit_code == 1
    assert RunStatus.PARTIAL.exit_code == 2


def test_module_entrypoint_starts():
    result = subprocess.run(
        [sys.executable, "-m", "gitbook_translator.cli", "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "--dictionary-path" in result.stdout
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
pytest tests/unit/test_models.py tests/integration/test_package_entrypoint.py -q
```

Expected: import failures because `gitbook_translator` does not exist.

- [ ] **Step 3: Add the minimal package and result types**

Implement:

```python
class RunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def exit_code(self) -> int:
        return {
            RunStatus.SUCCEEDED: 0,
            RunStatus.FAILED: 1,
            RunStatus.PARTIAL: 2,
            RunStatus.CANCELLED: 2,
        }[self]
```

Add Pydantic models for `ProviderSpec`, `TranslationJob`, `ProgressEvent`, `TranslationIssue`, `FileLanguageResult`, and `PipelineResult`. Configure:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["gitbook_translator*"]

[project.scripts]
gitbook-translator = "gitbook_translator.cli:main"
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
pytest tests/unit/test_models.py tests/integration/test_package_entrypoint.py -q
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/gitbook_translator tests/unit/test_models.py tests/integration/test_package_entrypoint.py
git commit -m "feat: establish installable translation package"
```

### Task 2: Implement configuration, repository, branch, and path safety

**Files:**
- Create: `src/gitbook_translator/config.py`
- Create: `src/gitbook_translator/paths.py`
- Test: `tests/unit/test_config.py`
- Test: `tests/unit/test_paths.py`

- [ ] **Step 1: Write failing validation tests**

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://github.com/acme/docs", "https://github.com/acme/docs"),
        ("https://github.com/acme/docs.git", "https://github.com/acme/docs"),
        ("https://github.com/acme/docs/", "https://github.com/acme/docs"),
    ],
)
def test_normalize_repository_url(value, expected):
    assert normalize_repository_url(value) == expected


def test_branch_allows_slashes():
    assert validate_branch("release/v1.0") == "release/v1.0"


@pytest.mark.parametrize("source", ["../escape.md", "/tmp/x.md", "C:\\x.md"])
def test_resolve_output_rejects_escape(tmp_path, source):
    with pytest.raises(ValueError):
        resolve_output_path(tmp_path, source, "en", "directory")
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_config.py tests/unit/test_paths.py -q
```

- [ ] **Step 3: Implement normalization and containment**

Use `urllib.parse`, `PurePosixPath`, and `Path.resolve()`. Enforce:

```python
root = output_root.resolve()
candidate = generated.resolve()
if not candidate.is_relative_to(root):
    raise ValueError("output path escapes configured root")
```

Reject branch `..`, `//`, `@{`, terminal `.`, `.lock`, control characters, and leading/trailing `/`; allow ordinary slash-separated refs.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_config.py tests/unit/test_paths.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/config.py src/gitbook_translator/paths.py tests/unit/test_config.py tests/unit/test_paths.py
git commit -m "feat: validate translation inputs and output containment"
```

### Task 3: Replace glossaries with language-specific dictionaries

**Files:**
- Create: `src/gitbook_translator/dictionaries.py`
- Create: `dictionaries/default/dictionary_en.json`
- Create: `dictionaries/default/dictionary_zh-cn.json`
- Create: `dictionaries/default/dictionary_zh-tw.json`
- Delete: `glossary.json`
- Delete: `glossary.example.json`
- Delete: `glossary_en.json`
- Delete: `glossary_zh-cn.json`
- Delete: `glossary_zh-tw.json`
- Test: `tests/unit/test_dictionaries.py`

- [ ] **Step 1: Write failing dictionary tests**

```python
def test_dictionary_filename_normalizes_language_case():
    assert dictionary_filename("zh-CN") == "dictionary_zh-cn.json"


def test_load_dictionary_returns_hash(tmp_path):
    (tmp_path / "dictionary_en.json").write_text('{"翻訳":"Translation"}')
    loaded = load_dictionary(tmp_path, "en")
    assert loaded.terms == {"翻訳": "Translation"}
    assert len(loaded.sha256) == 64


def test_loader_never_falls_back_to_glossary(tmp_path):
    (tmp_path / "glossary.json").write_text('{"翻訳":"Wrong"}')
    with pytest.raises(DictionaryNotFoundError):
        load_dictionary(tmp_path, "en")
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_dictionaries.py -q
```

- [ ] **Step 3: Implement strict flat-dictionary loading**

Validate a JSON object with non-empty string keys and values. Hash canonical UTF-8 JSON:

```python
canonical = json.dumps(terms, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

Move the existing three `dictionary_*.json` files into `dictionaries/default/`.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_dictionaries.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/dictionaries.py dictionaries tests/unit/test_dictionaries.py
git add -u glossary.json glossary.example.json glossary_en.json glossary_zh-cn.json glossary_zh-tw.json dictionary_en.json dictionary_zh-cn.json dictionary_zh-tw.json
git commit -m "feat: use language-specific dictionary sets"
```

### Task 4: Preserve Markdown structure with stable segment IDs

**Files:**
- Create: `src/gitbook_translator/markdown.py`
- Test: `tests/unit/test_markdown.py`
- Test: `tests/property/test_markdown_roundtrip.py`

- [ ] **Step 1: Write failing round-trip tests**

```python
def test_reconstruction_preserves_whitespace_around_code_block():
    source = '前文\n\n```python\nprint("x")\n```\n\n後文\n'
    document = parse_markdown(source)
    translated = {
        segment.id: segment.text.replace("前文", "Before").replace("後文", "After")
        for segment in document.translatable_segments
    }
    assert reconstruct(document, translated) == (
        'Before\n\n```python\nprint("x")\n```\n\nAfter\n'
    )


def test_response_rejects_duplicate_ids():
    with pytest.raises(InvalidProviderResponse):
        validate_segment_response(
            {"segment-0001"},
            {"segments": [
                {"id": "segment-0001", "translation": "A"},
                {"id": "segment-0001", "translation": "B"},
            ]},
        )
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_markdown.py tests/property/test_markdown_roundtrip.py -q
```

- [ ] **Step 3: Implement decomposition and reconstruction**

Represent translatable spans as:

```python
class TextSegment(BaseModel):
    id: str
    prefix: str
    text: str
    suffix: str
    start: int
    end: int
```

Separate structural whitespace before provider calls. Keep code fences, inline code, YAML frontmatter, GitBook expressions, HTML tags, and link destinations immutable. Reconstruct in original span order using original prefixes and suffixes.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_markdown.py tests/property/test_markdown_roundtrip.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/markdown.py tests/unit/test_markdown.py tests/property/test_markdown_roundtrip.py
git commit -m "feat: preserve markdown with structured segments"
```

### Task 5: Add lazy OpenAI, Gemini, and Ollama provider adapters

**Files:**
- Create: `src/gitbook_translator/providers/base.py`
- Create: `src/gitbook_translator/providers/factory.py`
- Create: `src/gitbook_translator/providers/openai_provider.py`
- Create: `src/gitbook_translator/providers/gemini_provider.py`
- Create: `src/gitbook_translator/providers/ollama_provider.py`
- Create: `src/gitbook_translator/providers/__init__.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/providers/test_factory.py`
- Test: `tests/unit/providers/test_openai.py`
- Test: `tests/unit/providers/test_gemini.py`
- Test: `tests/unit/providers/test_ollama.py`

- [ ] **Step 1: Write failing lazy-provider tests**

```python
def test_factory_does_not_require_unselected_provider_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = create_provider(ProviderSpec(provider="ollama", model="qwen3"))
    assert provider.name == "ollama"


def test_ollama_healthcheck_lists_requested_model(httpx_mock):
    httpx_mock.add_response(
        url="http://127.0.0.1:11434/api/tags",
        json={"models": [{"name": "qwen3:latest"}]},
    )
    assert OllamaProvider(model="qwen3:latest").healthcheck().available is True
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/providers -q
```

- [ ] **Step 3: Implement the protocol and adapters**

Define:

```python
class TranslationProvider(Protocol):
    name: str
    model: str
    def healthcheck(self) -> ProviderHealth:
        raise NotImplementedError
    def translate(self, request: TranslationRequest) -> SegmentResponse:
        raise NotImplementedError
    def review(self, request: ReviewRequest) -> ReviewResponse:
        raise NotImplementedError
    def correct(self, request: CorrectionRequest) -> SegmentResponse:
        raise NotImplementedError
```

Import SDK modules only inside selected factory branches. OpenAI and Gemini request structured JSON. Ollama uses `/api/tags` and `/api/chat` with `stream: false`. Replace LangChain runtime dependencies with direct SDK dependencies:

```toml
"openai>=1.0,<3",
"google-genai>=1.0,<3",
"httpx>=0.27,<1",
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/providers -q
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/gitbook_translator/providers tests/unit/providers
git commit -m "feat: add openai gemini and ollama providers"
```

### Task 6: Add mechanical verification

**Files:**
- Create: `src/gitbook_translator/verification.py`
- Test: `tests/unit/test_verification.py`

- [ ] **Step 1: Write failing verifier tests**

```python
def test_verifier_detects_changed_link_destination():
    issues = verify_translation(
        original="[文書](../guide.md)",
        translated="[Document](../other.md)",
        dictionary={},
        language="en",
    )
    assert any(i.code == "link_changed" and i.severity == "BLOCKER" for i in issues)


def test_verifier_detects_dictionary_violation():
    issues = verify_translation(
        original="帳票定義を開く",
        translated="Open the Form Definition",
        dictionary={"帳票定義": "Template Form"},
        language="en",
    )
    assert any(i.code == "dictionary_violation" for i in issues)
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_verification.py -q
```

- [ ] **Step 3: Implement deterministic checks**

Compare protected spans and link destinations exactly. Detect Japanese only in translatable spans. Require exact target dictionary terms when source terms appear. Return typed issues; an LLM approval cannot override mechanical BLOCKER or MAJOR issues.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_verification.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/verification.py tests/unit/test_verification.py
git commit -m "feat: add mechanical translation verification"
```

### Task 7: Implement fingerprint cache and atomic saving

**Files:**
- Create: `src/gitbook_translator/cache.py`
- Create: `src/gitbook_translator/storage.py`
- Test: `tests/unit/test_cache.py`
- Test: `tests/unit/test_storage.py`

- [ ] **Step 1: Write failing cache regression tests**

```python
def test_existing_entry_updates_source_hash_and_commit(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    cache.record_success(fingerprint(source_sha256="old", source_commit="a"))
    cache.record_success(fingerprint(source_sha256="new", source_commit="b"))
    entry = cache.get(KEY)
    assert entry.source_sha256 == "new"
    assert entry.source_commit == "b"


def test_new_language_is_cache_miss(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    cache.record_success(fingerprint(language="en"))
    assert cache.lookup(fingerprint(language="zh-CN")).hit is False
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_cache.py tests/unit/test_storage.py -q
```

- [ ] **Step 3: Implement complete fingerprints**

Include repository, branch, source path/hash, language, dictionary hash, providers/models, pipeline version, and output path. Save to a temporary sibling then call `os.replace`; update cache only after output replacement succeeds. Treat legacy cache versions as empty.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_cache.py tests/unit/test_storage.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/cache.py src/gitbook_translator/storage.py tests/unit/test_cache.py tests/unit/test_storage.py
git commit -m "feat: add complete translation cache fingerprints"
```

### Task 8: Replace silent GitHub operations with explicit results

**Files:**
- Create: `src/gitbook_translator/github_client.py`
- Test: `tests/unit/test_github_client.py`
- Test: `tests/integration/test_github_push.py`

- [ ] **Step 1: Write failing fetch and confirmation tests**

```python
def test_fetch_reports_inaccessible_file(fake_repo):
    fake_repo.fail_contents("docs/private.md", status=403)
    result = GitHubSource(fake_repo).fetch(["docs/**/*.md"], "main")
    assert result.status == "partial"
    assert result.errors[0].path == "docs/private.md"


def test_direct_push_requires_confirmation(fake_repo):
    with pytest.raises(DirectPushNotConfirmed):
        GitHubPublisher(fake_repo).publish(
            branch="main",
            files=[OutputFile(path="README.en.md", content="x")],
            strategy="push_same_repo_direct",
            direct_push_confirmed=False,
        )
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_github_client.py tests/integration/test_github_push.py -q
```

- [ ] **Step 3: Implement structured fetch and push**

Return `FetchResult(files, errors, status)` and `PublishResult`; never `continue` or `pass` an inaccessible path. Normalize `.git` URLs, return compare URLs, and accept direct confirmation only from trusted configuration.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_github_client.py tests/integration/test_github_push.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/github_client.py tests/unit/test_github_client.py tests/integration/test_github_push.py
git commit -m "feat: make github operations explicit and safe"
```

### Task 9: Build the deterministic pipeline and event stream

**Files:**
- Create: `src/gitbook_translator/pipeline.py`
- Create: `src/gitbook_translator/events.py`
- Test: `tests/unit/test_pipeline.py`
- Test: `tests/integration/test_pipeline_flow.py`

- [ ] **Step 1: Write failing orchestration tests**

```python
def test_pipeline_uses_fixed_stage_order(fakes, job):
    events = []
    result = TranslationPipeline(**fakes).run(job, events.append)
    assert [e.stage for e in events if e.kind == "stage"] == [
        "validate", "fetch", "dictionary", "translate",
        "verify", "save", "complete",
    ]
    assert result.status == RunStatus.SUCCEEDED


def test_one_language_failure_produces_partial(fakes, multi_language_job):
    fakes.providers.fail_language("zh-CN")
    result = TranslationPipeline(**fakes).run(multi_language_job)
    assert result.status == RunStatus.PARTIAL
    assert result.success_count == 1
    assert result.failure_count == 1
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_pipeline.py tests/integration/test_pipeline_flow.py -q
```

- [ ] **Step 3: Implement explicit orchestration**

Inject source, publisher, provider factory, cache, storage, clock, and cancellation probe. Iterate files and languages explicitly, check cancellation before each external call and correction loop, enforce file size, emit typed events, always run mechanical verification, and return `partial` for mixed outcomes.

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_pipeline.py tests/integration/test_pipeline_flow.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/pipeline.py src/gitbook_translator/events.py tests/unit/test_pipeline.py tests/integration/test_pipeline_flow.py
git commit -m "feat: add deterministic translation pipeline"
```

### Task 10: Repair CLI behavior and remove the ReAct runtime

**Files:**
- Modify: `src/gitbook_translator/cli.py`
- Modify: `.env.example`
- Modify: `requirements.txt`
- Delete: `src/agent/`
- Delete: migrated legacy modules under `src/tools/`
- Test: `tests/integration/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
@pytest.mark.parametrize(
    ("status", "code"),
    [
        (RunStatus.SUCCEEDED, 0),
        (RunStatus.FAILED, 1),
        (RunStatus.PARTIAL, 2),
    ],
)
def test_cli_returns_pipeline_exit_code(monkeypatch, status, code):
    monkeypatch.setattr(cli, "run_translation", lambda _: PipelineResult(status=status))
    assert cli.main(VALID_ARGS) == code


def test_glossary_flag_has_migration_error(capsys):
    code = cli.main(["translate", "--glossary-path", "glossary.json"])
    assert code == 1
    assert "use --dictionary-path" in capsys.readouterr().err
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/integration/test_cli.py -q
```

- [ ] **Step 3: Implement truthful CLI behavior**

Add `translate` as the default-compatible operation and reserve `worker` for phase 2. Check only selected provider credentials. Remove Anthropic text. Render summaries and return integer codes instead of calling `sys.exit` inside testable functions.

- [ ] **Step 4: Run phase tests**

```bash
pytest tests/unit tests/property tests/integration -q
```

- [ ] **Step 5: Commit**

```bash
git add src/gitbook_translator/cli.py .env.example requirements.txt tests/integration/test_cli.py
git add -u src/agent src/tools
git commit -m "feat: replace react agent with deterministic cli"
```

### Task 11: Verify wheel installation and remove generated artifacts

**Files:**
- Modify: `.gitignore`
- Delete: `build/`
- Delete: `src/gitbook_translator.egg-info/`
- Test: `tests/integration/test_wheel_install.py`

- [ ] **Step 1: Write the wheel smoke test**

Build and install a wheel into a temporary virtual environment, change its working directory to `/tmp`, and run:

```bash
gitbook-translator --help
gitbook-translator translate --help
```

Assert code `0` and the presence of `--dictionary-path`, `ollama`, and `--confirm-direct-push`.

- [ ] **Step 2: Verify RED**

```bash
pytest tests/integration/test_wheel_install.py -q
```

- [ ] **Step 3: Clean package metadata**

Remove tracked build output and egg-info. Add optional test dependencies for `pytest-httpx`, `build`, and Hypothesis and ensure `.gitignore` covers generated artifacts.

- [ ] **Step 4: Run release checks**

```bash
python -m build
pytest tests/unit tests/property tests/integration -q
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore tests/integration/test_wheel_install.py
git add -u build src/gitbook_translator.egg-info
git commit -m "build: verify distributable cli package"
```
