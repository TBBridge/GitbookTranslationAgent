from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_release_scripts_exist_are_executable_and_run_expected_commands():
    expected = {
        "verify-python-release.sh": ["pytest", "python -m build", "worker --help"],
        "verify-web-release.sh": ["npm run lint", "npm run typecheck", "npm run build", "npm run test:e2e"],
        "verify-all.sh": ["verify-python-release.sh", "verify-web-release.sh", "git diff --check"],
    }

    for name, commands in expected.items():
        path = ROOT / "scripts" / name
        assert path.exists()
        assert os.access(path, os.X_OK)
        content = path.read_text(encoding="utf-8")
        assert "set -euo pipefail" in content
        for command in commands:
            assert command in content
