from pathlib import Path

from gitbook_translator.cache import TranslationCache, TranslationFingerprint


def fingerprint(**overrides):
    values = {
        "repository_url": "https://github.com/acme/docs",
        "branch": "main",
        "source_path": "docs/index.md",
        "source_sha256": "source",
        "source_commit": "commit",
        "language": "en",
        "dictionary_sha256": "dictionary",
        "translation_provider": "ollama",
        "translation_model": "qwen3",
        "review_provider": "none",
        "review_model": "none",
        "pipeline_version": "1",
        "output_path": "out/en/docs/index.md",
    }
    values.update(overrides)
    return TranslationFingerprint(**values)


def test_existing_entry_updates_source_hash_and_commit(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    old = fingerprint(source_sha256="old", source_commit="a")
    new = fingerprint(source_sha256="new", source_commit="b")
    key = cache.cache_key(old)

    cache.record_success(old)
    cache.record_success(new)

    entry = cache.get(key)
    assert entry is not None
    assert entry.source_sha256 == "new"
    assert entry.source_commit == "b"


def test_new_language_is_cache_miss(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    cache.record_success(fingerprint(language="en"))

    assert cache.lookup(fingerprint(language="zh-CN")).hit is False


def test_changed_dictionary_hash_is_cache_miss(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    output = tmp_path / "out.md"
    output.write_text("translated", encoding="utf-8")
    cache.record_success(fingerprint(dictionary_sha256="old", output_path=str(output)))

    lookup = cache.lookup(fingerprint(dictionary_sha256="new", output_path=str(output)))

    assert lookup.hit is False
    assert lookup.reason == "fingerprint_changed"


def test_legacy_cache_version_is_treated_as_empty(tmp_path):
    (tmp_path / "cache.json").write_text('{"version": 0, "entries": {"x": {}}}')

    cache = TranslationCache(tmp_path / "cache.json")

    assert cache.get("x") is None


def test_cache_persists_records(tmp_path):
    path = tmp_path / "cache.json"
    output = tmp_path / "out.md"
    output.write_text("translated", encoding="utf-8")
    fp = fingerprint(output_path=str(output))
    first = TranslationCache(path)
    first.record_success(fp)

    second = TranslationCache(path)

    assert second.lookup(fp).hit is True


def test_missing_output_file_is_cache_miss(tmp_path):
    cache = TranslationCache(tmp_path / "cache.json")
    fp = fingerprint(output_path=str(tmp_path / "missing.md"))
    cache.record_success(fp)

    lookup = cache.lookup(fp)

    assert lookup.hit is False
    assert lookup.reason == "output_missing"
