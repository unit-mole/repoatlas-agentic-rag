import subprocess
from pathlib import Path


def commit_summary(repo: Path, commit: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", "--no-patch", "--format=%H%n%ct%n%s%n%b", commit],
        text=True,
        errors="replace",
    )
