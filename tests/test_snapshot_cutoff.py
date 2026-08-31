import subprocess
from pathlib import Path

import pytest

from repoatlas.repositories.snapshots import create_snapshot
from repoatlas.tools.git_tools import GitCutoffViolation, GitTools


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message], check=True, capture_output=True
    )
    return _git(repo, "rev-parse", "HEAD")


def test_snapshot_is_exact_base_commit_and_git_tools_block_future(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)

    (repo / "value.txt").write_text("before\n", encoding="utf-8")
    base = _commit(repo, "base")
    (repo / "value.txt").write_text("after\n", encoding="utf-8")
    future = _commit(repo, "future fix")

    snapshot = tmp_path / "snapshot"
    resolved = create_snapshot(repo, snapshot, base)
    assert resolved == base
    assert (snapshot / "value.txt").read_text(encoding="utf-8") == "before\n"
    assert not (snapshot / ".git").exists()

    tools = GitTools(repo, base_commit=base)
    assert tools.get_commit_summary(base)
    with pytest.raises(GitCutoffViolation):
        tools.get_commit_summary(future)
