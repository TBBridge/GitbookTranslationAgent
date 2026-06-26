from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
WORKER_DOCS = (ROOT / "docs" / "worker-setup.md").read_text(encoding="utf-8")
DEPLOYMENT_DOCS = (ROOT / "docs" / "web-deployment.md").read_text(encoding="utf-8")
MIGRATION_DOCS = (ROOT / "docs" / "migration-from-glossary.md").read_text(
    encoding="utf-8"
)


def test_documentation_matches_supported_features():
    assert "--dictionary-path" in README
    assert "--glossary-path" not in README
    assert "gitbook-translator worker" in WORKER_DOCS
    assert "dictionary_zh-cn.json" in MIGRATION_DOCS
    assert "Vercel Blob" not in DEPLOYMENT_DOCS
    assert "Ollama" in README
    assert "Neon" in DEPLOYMENT_DOCS
