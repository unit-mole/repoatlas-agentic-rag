import subprocess
from pathlib import Path


def file_history(
    repo: Path, file_path: str, base_commit: str = "HEAD", limit: int = 20
) -> list[dict]:
    fmt = "%H%x1f%ct%x1f%s"
    raw = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "log",
            f"-{limit}",
            f"--format={fmt}",
            base_commit,
            "--",
            file_path,
        ],
        text=True,
        errors="replace",
    )
    return [
        dict(zip(["commit", "timestamp", "subject"], line.split("\x1f", 2)))
        for line in raw.splitlines()
        if line
    ]
