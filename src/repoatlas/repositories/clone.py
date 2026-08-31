import subprocess
from pathlib import Path


def clone_repository(url: str, destination: Path, commit: str | None = None) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    subprocess.run(["git", "clone", "--no-tags", url, str(destination)], check=True, timeout=300)
    if commit:
        subprocess.run(
            ["git", "-C", str(destination), "checkout", "--detach", commit], check=True, timeout=60
        )
    return subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True
    ).strip()
