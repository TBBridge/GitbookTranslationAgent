import pytest

from gitbook_translator.github_client import GitHubSource


class FakeGitHubError(Exception):
    def __init__(self, status):
        super().__init__(f"GitHub status {status}")
        self.status = status


class FakeContent:
    def __init__(self, path, content):
        self.path = path
        self.decoded_content = content.encode("utf-8")
        self.sha = f"sha-{path}"


class FakeRepo:
    def __init__(self):
        self.files = {
            "docs/index.md": "# はじめに",
            "docs/private.md": "# private",
            "docs/nested/guide.md": "# ガイド",
        }
        self.failures = {}

    def fail_contents(self, path, status):
        self.failures[path] = status

    def list_paths(self, branch):
        assert branch == "main"
        return sorted(self.files)

    def get_contents(self, path, ref):
        assert ref == "main"
        if path in self.failures:
            raise FakeGitHubError(self.failures[path])
        return FakeContent(path, self.files[path])


def test_fetch_reports_inaccessible_file():
    fake_repo = FakeRepo()
    fake_repo.fail_contents("docs/private.md", status=403)

    result = GitHubSource(fake_repo).fetch(["docs/**/*.md"], "main")

    assert result.status == "partial"
    assert result.errors[0].path == "docs/private.md"
    assert result.errors[0].status == 403
    assert {file.path for file in result.files} == {
        "docs/index.md",
        "docs/nested/guide.md",
    }


def test_fetch_returns_failed_when_all_files_are_inaccessible():
    fake_repo = FakeRepo()
    for path in fake_repo.files:
        fake_repo.fail_contents(path, status=404)

    result = GitHubSource(fake_repo).fetch(["docs/**/*.md"], "main")

    assert result.status == "failed"
    assert result.files == []
    assert len(result.errors) == 3


def test_fetch_reports_no_matching_files():
    result = GitHubSource(FakeRepo()).fetch(["missing/**/*.md"], "main")

    assert result.status == "failed"
    assert result.errors[0].code == "no_matching_files"


def test_fetch_success_decodes_content():
    result = GitHubSource(FakeRepo()).fetch(["docs/index.md"], "main")

    assert result.status == "succeeded"
    assert result.files[0].path == "docs/index.md"
    assert result.files[0].content == "# はじめに"
