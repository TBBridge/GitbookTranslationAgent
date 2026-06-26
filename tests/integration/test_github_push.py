import pytest

from gitbook_translator.github_client import (
    DirectPushNotConfirmed,
    GitHubPublisher,
    OutputFile,
)


class FakeRepo:
    def __init__(self):
        self.writes = []

    def upsert_file(self, path, content, branch, message):
        self.writes.append(
            {
                "path": path,
                "content": content,
                "branch": branch,
                "message": message,
            }
        )

    def compare_url(self, branch):
        return f"https://github.com/acme/docs/compare/{branch}"


def test_direct_push_requires_confirmation():
    fake_repo = FakeRepo()

    with pytest.raises(DirectPushNotConfirmed):
        GitHubPublisher(fake_repo).publish(
            branch="main",
            files=[OutputFile(path="README.en.md", content="x")],
            strategy="push_same_repo_direct",
            direct_push_confirmed=False,
        )

    assert fake_repo.writes == []


def test_direct_push_writes_when_confirmed():
    fake_repo = FakeRepo()

    result = GitHubPublisher(fake_repo).publish(
        branch="main",
        files=[OutputFile(path="README.en.md", content="x")],
        strategy="push_same_repo_direct",
        direct_push_confirmed=True,
    )

    assert result.status == "succeeded"
    assert fake_repo.writes[0]["path"] == "README.en.md"


def test_none_strategy_skips_remote_writes():
    fake_repo = FakeRepo()

    result = GitHubPublisher(fake_repo).publish(
        branch="main",
        files=[OutputFile(path="README.en.md", content="x")],
        strategy="none",
    )

    assert result.status == "skipped"
    assert fake_repo.writes == []
