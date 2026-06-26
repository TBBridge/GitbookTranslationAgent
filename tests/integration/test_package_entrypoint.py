import os
import subprocess
import sys
from pathlib import Path


def test_module_entrypoint_starts():
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    pythonpath = os.pathsep.join(
        path for path in (src_path, os.environ.get("PYTHONPATH", "")) if path
    )
    result = subprocess.run(
        [sys.executable, "-m", "gitbook_translator.cli", "--help"],
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": pythonpath},
    )
    assert result.returncode == 0
    assert "--dictionary-path" in result.stdout
