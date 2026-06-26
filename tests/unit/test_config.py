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


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/acme",
        "https://github.com/acme/docs/tree/main",
    ],
)
def test_normalize_repository_url_rejects_paths_without_exact_owner_repo(value):
    with pytest.raises(ValueError):
        normalize_repository_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/acme/docs?tab=readme",
        "https://github.com/acme/docs#readme",
        "https://github.com/acme/docs;download",
    ],
)
def test_normalize_repository_url_rejects_params_query_and_fragment(value):
    with pytest.raises(ValueError):
        normalize_repository_url(value)


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
