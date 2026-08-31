import subprocess
from pathlib import Path


def blame_context(
    repo: Path, file_path: str, start: int, end: int, base_commit: str = "HEAD"
) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "blame", base_commit, f"-L{start},{end}", "--", file_path],
        text=True,
        errors="replace",
    )
