from pathlib import Path

from repoatlas.parsing.python_parser import extract_python_symbols
from repoatlas.repositories.scanner import scan_repository


def extract_repository_symbols(repo_id: str, root: Path, commit_hash: str | None = None):
    out = []
    for f in scan_repository(repo_id, root):
        out.extend(extract_python_symbols(repo_id, root / f.path, root, commit_hash))
    return out
