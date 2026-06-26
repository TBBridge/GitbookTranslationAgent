import pytest

from gitbook_translator.dictionaries import (
    DictionaryNotFoundError,
    dictionary_filename,
    load_dictionary,
)


def test_dictionary_filename_normalizes_language_case():
    assert dictionary_filename("zh-CN") == "dictionary_zh-cn.json"


def test_load_dictionary_returns_hash(tmp_path):
    (tmp_path / "dictionary_en.json").write_text(
        '{"翻訳":"Translation"}',
        encoding="utf-8",
    )
    loaded = load_dictionary(tmp_path, "en")
    assert loaded.terms == {"翻訳": "Translation"}
    assert len(loaded.sha256) == 64


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
