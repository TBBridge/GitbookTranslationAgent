"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_markdown():
    """Sample GitBook markdown content for testing."""
    return """# Test Document

This is a test document with Japanese text: これはテストです。

```python
def hello():
    print("Hello, World!")
```

[Link text](https://example.com)

![Image alt](./image.png)
"""
