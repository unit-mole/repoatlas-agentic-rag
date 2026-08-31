import subprocess
from pathlib import Path


def diff(repo: Path, rev_a: str, rev_b: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "diff", rev_a, rev_b, "--"], text=True, errors="replace"
    )
