import subprocess
import sys
import venv
from pathlib import Path


def test_wheel_installs_cli_outside_repository(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    wheel = next(dist.glob("gitbook_translator-*.whl"))

    venv_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    command = venv_dir / (
        "Scripts/gitbook-translator.exe"
        if sys.platform == "win32"
        else "bin/gitbook-translator"
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", str(wheel)],
        text=True,
        capture_output=True,
        check=True,
    )

    root_help = subprocess.run(
        [str(command), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    translate_help = subprocess.run(
        [str(command), "translate", "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )

    combined_help = root_help.stdout + translate_help.stdout
    assert "--dictionary-path" in combined_help
    assert "ollama" in combined_help
    assert "--confirm-direct-push" in combined_help
