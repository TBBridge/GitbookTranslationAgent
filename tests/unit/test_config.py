import pytest

from gitbook_translator.config import normalize_repository_url, validate_branch


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


@pytest.mark.parametrize(
    "value",
    [
        "../main",
        "feature//x",
        "feature@{x",
        "release.",
        "feature.lock",
        "feature/\nmain",
        "/main",
        "main/",
    ],
)
def test_branch_rejects_unsafe_refs(value):
    with pytest.raises(ValueError):
        validate_branch(value)
