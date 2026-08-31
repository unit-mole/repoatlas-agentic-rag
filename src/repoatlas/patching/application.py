import subprocess
from pathlib import Path


def apply_unified_patch(workspace: Path, patch: str):
    p = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=workspace,
        input=patch,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    return {"ok": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr}


def workspace_diff(workspace: Path):
    return (
        subprocess.check_output(
            ["git", "diff", "--no-ext-diff"], cwd=workspace, text=True, errors="replace"
        )
        if (workspace / ".git").exists()
        else ""
    )
