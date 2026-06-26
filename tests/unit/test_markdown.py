import pytest

from gitbook_translator.markdown import (
    InvalidProviderResponse,
    parse_markdown,
    reconstruct,
    validate_segment_response,
)


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


def test_reconstruction_preserves_inline_code_and_link_destination():
    source = "詳細は `run()` と [文書](../guide.md) を参照してください。\n"
    document = parse_markdown(source)
    translated = {
        segment.id: (
            segment.text.replace("詳細は", "See")
            .replace("文書", "Document")
            .replace("を参照してください。", "for details.")
        )
        for segment in document.translatable_segments
    }

    assert reconstruct(document, translated) == (
        "See `run()` と [Document](../guide.md) for details.\n"
    )


def test_reconstruction_preserves_yaml_gitbook_and_html_tags():
    source = "---\ntitle: テスト\n---\n\n{% hint style=\"info\" %}\n<strong>本文</strong>\n{% endhint %}\n"
    document = parse_markdown(source)
    translated = {
        segment.id: segment.text.replace("本文", "Body")
        for segment in document.translatable_segments
    }

    assert reconstruct(document, translated) == (
        "---\ntitle: テスト\n---\n\n{% hint style=\"info\" %}\n<strong>Body</strong>\n{% endhint %}\n"
    )


def test_segment_ids_are_stable_and_ordered():
    document = parse_markdown("一つ目\n\n二つ目\n")
    assert [segment.id for segment in document.translatable_segments] == [
        "segment-0001",
        "segment-0002",
    ]


def test_response_rejects_duplicate_ids():
    with pytest.raises(InvalidProviderResponse):
        validate_segment_response(
            {"segment-0001"},
            {
                "segments": [
                    {"id": "segment-0001", "translation": "A"},
                    {"id": "segment-0001", "translation": "B"},
                ]
            },
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"segments": [{"translation": "A"}]},
        {"segments": [{"id": "segment-0002", "translation": "A"}]},
        {"segments": [{"id": "segment-0001", "translation": 123}]},
        {"segments": []},
    ],
)
def test_response_rejects_invalid_provider_payloads(payload):
    with pytest.raises(InvalidProviderResponse):
        validate_segment_response({"segment-0001"}, payload)


def test_response_returns_translation_mapping():
    assert validate_segment_response(
        {"segment-0001"},
        {"segments": [{"id": "segment-0001", "translation": "Translated"}]},
    ) == {"segment-0001": "Translated"}
