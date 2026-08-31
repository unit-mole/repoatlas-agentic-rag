from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
from pathlib import Path

from repoatlas.security.path_validation import safe_resolve


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def _safe_extract_tar(payload: bytes, destination: Path) -> None:
    """Extract a git archive while rejecting absolute/traversal paths."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                # Frozen benchmark snapshots intentionally avoid symlinks. This keeps
                # repository reads inside the snapshot root on all platforms.
                continue
            safe_resolve(destination, member.name, must_exist=False)
        try:
            archive.extractall(destination, filter="data")
        except TypeError:  # Python <3.12 compatibility for contributors.
            archive.extractall(destination)


def create_snapshot(repo: Path, destination: Path, base_commit: str = "HEAD") -> str:
    """Freeze *exactly* ``base_commit`` into a Git-metadata-free directory.

    Historical evaluation must operate on the repository state before the gold fix.
    Using ``git archive`` prevents accidentally copying a later checkout and removes
    ``.git`` metadata, so the agent cannot inspect future commits from the snapshot.
    """
    repo = repo.resolve()
    commit = _git(repo, "rev-parse", f"{base_commit}^{{commit}}")
    payload = subprocess.check_output(
        ["git", "-C", str(repo), "archive", "--format=tar", commit],
        stderr=subprocess.STDOUT,
    )
    if destination.exists():
        shutil.rmtree(destination)
    _safe_extract_tar(payload, destination)
    (destination / ".repoatlas_base_commit").write_text(commit + "\n", encoding="utf-8")
    return commit
