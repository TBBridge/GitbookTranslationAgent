from gitbook_translator.verification import verify_translation


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


def test_verifier_detects_changed_code_fence_content():
    issues = verify_translation(
        original='説明\n\n```python\nprint("x")\n```\n',
        translated='Description\n\n```python\nprint("y")\n```\n',
        dictionary={},
        language="en",
    )

    assert any(i.code == "protected_changed" and i.severity == "BLOCKER" for i in issues)


def test_verifier_detects_untranslated_japanese_in_translatable_text():
    issues = verify_translation(
        original="説明です",
        translated="This is 説明",
        dictionary={},
        language="en",
    )

    assert any(i.code == "untranslated_japanese" and i.severity == "MAJOR" for i in issues)


def test_verifier_ignores_japanese_inside_protected_code():
    issues = verify_translation(
        original='説明\n\n```\n日本語\n```\n',
        translated='Description\n\n```\n日本語\n```\n',
        dictionary={},
        language="en",
    )

    assert not any(i.code == "untranslated_japanese" for i in issues)


def test_verifier_accepts_matching_mechanical_invariants():
    issues = verify_translation(
        original="[帳票定義](../guide.md) と `コード`",
        translated="[Template Form](../guide.md) and `コード`",
        dictionary={"帳票定義": "Template Form"},
        language="en",
    )

    assert issues == []
