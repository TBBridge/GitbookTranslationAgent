import pytest

from gitbook_translator.paths import resolve_output_path


def test_resolve_output_directory_uses_language_subdirectory(tmp_path):
    assert (
        resolve_output_path(tmp_path, "docs/guide.md", "en", "directory")
        == tmp_path.resolve() / "en" / "docs" / "guide.md"
    )


@pytest.mark.parametrize("source", ["../escape.md", "/tmp/x.md", "C:\\x.md", "C:/x.md"])
def test_resolve_output_rejects_escape(tmp_path, source):
    with pytest.raises(ValueError):
        resolve_output_path(tmp_path, source, "en", "directory")


@pytest.mark.parametrize("source", ["docs/../escape.md", "docs\\escape.md"])
def test_resolve_output_rejects_unsafe_relative_paths(tmp_path, source):
    with pytest.raises(ValueError):
        resolve_output_path(tmp_path, source, "en", "directory")
