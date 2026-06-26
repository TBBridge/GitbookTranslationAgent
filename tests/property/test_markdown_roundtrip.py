from hypothesis import given, strategies as st

from gitbook_translator.markdown import parse_markdown, reconstruct


safe_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cc", "Cs"),
        blacklist_characters="`<>{}[]()\n\r",
    ),
    min_size=1,
    max_size=30,
)

whitespace = st.text(alphabet=" \t\n", min_size=0, max_size=5)


@given(prefix=whitespace, text=safe_text, suffix=whitespace)
def test_identity_translation_round_trips_simple_text(prefix, text, suffix):
    source = f"{prefix}{text}{suffix}"
    document = parse_markdown(source)
    translated = {
        segment.id: segment.text for segment in document.translatable_segments
    }

    assert reconstruct(document, translated) == source


@given(before=safe_text, after=safe_text)
def test_code_fence_round_trips_with_identity_translation(before, after):
    source = f"{before}\n\n```\nprotected()\n```\n\n{after}\n"
    document = parse_markdown(source)
    translated = {
        segment.id: segment.text for segment in document.translatable_segments
    }

    assert reconstruct(document, translated) == source
