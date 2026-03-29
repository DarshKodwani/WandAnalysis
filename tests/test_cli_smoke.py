import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_help(script_name: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script_name), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_commands_run() -> None:
    scripts = [
        "batch_qc.py",
        "visualise_bold.py",
        "slice_qc.py",
        "iqm.py",
        "group_qc.py",
        "compare_3t_7t_mriqc.py",
    ]

    for script in scripts:
        result = run_help(script)
        assert result.returncode == 0, f"{script} failed help output: {result.stderr}"
        assert "usage" in result.stdout.lower()
