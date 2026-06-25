import subprocess
import sys


def test_module_entrypoint_starts():
    result = subprocess.run(
        [sys.executable, "-m", "gitbook_translator.cli", "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "--dictionary-path" in result.stdout
