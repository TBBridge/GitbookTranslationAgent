"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_config():
    """Sample CLI configuration for testing."""
    from src.models import CLIConfig

    return CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="./output",
    )


@pytest.fixture
def sample_markdown():
    """Sample markdown content for testing."""
    return """# Test Document

This is a test document with Japanese text: これはテストです。

```python
def hello():
    print("Hello, World!")
```

[Link text](https://example.com)

![Image alt](./image.png)
"""


@pytest.fixture
def sample_glossary():
    """Sample glossary for testing."""
    return {
        "terms": [
            {
                "ja": "帳票定義",
                "en": "Template Form",
                "zh-CN": "报表定义",
            }
        ]
    }
