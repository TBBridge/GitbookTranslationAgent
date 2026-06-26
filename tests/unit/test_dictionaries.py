import hashlib
from pathlib import Path

import pytest

from gitbook_translator.dictionaries import (
    DictionaryNotFoundError,
    dictionary_filename,
    load_dictionary,
)


def test_dictionary_filename_normalizes_language_case():
    assert dictionary_filename("zh-CN") == "dictionary_zh-cn.json"


@pytest.mark.parametrize(
    "language",
    [
        "",
        "x/../../secret",
        r"zh\CN",
        ".",
        "..",
        "-en",
    ],
)
def test_dictionary_filename_rejects_unsafe_languages(language):
    with pytest.raises(ValueError, match="language"):
        dictionary_filename(language)


@pytest.mark.parametrize(
    "language",
    [
        "",
        "x/../../secret",
        r"zh\CN",
        ".",
        "..",
        "-en",
    ],
)
def test_load_dictionary_rejects_unsafe_languages_before_filesystem_lookup(
    tmp_path,
    monkeypatch,
    language,
):
    def fail_filesystem_lookup(path):
        pytest.fail(f"unexpected filesystem lookup for {path}")

    monkeypatch.setattr(Path, "is_file", fail_filesystem_lookup)

    with pytest.raises(ValueError, match="language"):
        load_dictionary(tmp_path, language)


def test_load_dictionary_returns_hash(tmp_path):
    (tmp_path / "dictionary_en.json").write_text(
        '{"翻訳":"Translation"}',
        encoding="utf-8",
    )
    loaded = load_dictionary(tmp_path, "en")
    assert loaded.terms == {"翻訳": "Translation"}
    assert len(loaded.sha256) == 64


def test_load_dictionary_hashes_canonical_sorted_utf8_terms(tmp_path):
    (tmp_path / "dictionary_en.json").write_text(
        '{"b":"β","a":"α"}',
        encoding="utf-8",
    )

    loaded = load_dictionary(tmp_path, "en")

    expected = hashlib.sha256('{"a":"α","b":"β"}'.encode("utf-8")).hexdigest()
    assert loaded.sha256 == expected


def test_loader_never_falls_back_to_glossary(tmp_path):
    (tmp_path / "glossary.json").write_text(
        '{"翻訳":"Wrong"}',
        encoding="utf-8",
    )
    with pytest.raises(DictionaryNotFoundError):
        load_dictionary(tmp_path, "en")


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        '{"": "Translation"}',
        '{"翻訳": ""}',
        '{"翻訳": 123}',
        '{"翻訳": {"nested": "Translation"}}',
    ],
)
def test_load_dictionary_requires_flat_non_empty_strings(tmp_path, content):
    (tmp_path / "dictionary_en.json").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_dictionary(tmp_path, "en")
