import shutil
from pathlib import Path


def cleanup_workspace(path: Path):
    if path.exists():
        shutil.rmtree(path)
