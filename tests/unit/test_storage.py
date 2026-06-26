import os

import pytest

from gitbook_translator.cache import TranslationCache
from gitbook_translator.storage import atomic_write_text, save_output_and_record
from tests.unit.test_cache import fingerprint


def test_atomic_write_text_replaces_file(tmp_path):
    path = tmp_path / "output.md"
    path.write_text("old", encoding="utf-8")

    atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "new"
    assert not list(tmp_path.glob(".output.md.*.tmp"))


def test_save_output_records_cache_after_successful_replacement(tmp_path):
    output = tmp_path / "out.md"
    cache = TranslationCache(tmp_path / "cache.json")
    fp = fingerprint(output_path=str(output))

    save_output_and_record(output, "translated", cache, fp)

    assert output.read_text(encoding="utf-8") == "translated"
    assert cache.lookup(fp).hit is True


def test_save_output_does_not_record_cache_when_replacement_fails(tmp_path, monkeypatch):
    output = tmp_path / "out.md"
    cache = TranslationCache(tmp_path / "cache.json")
    fp = fingerprint(output_path=str(output))

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError):
        save_output_and_record(output, "translated", cache, fp)

    assert cache.lookup(fp).hit is False
