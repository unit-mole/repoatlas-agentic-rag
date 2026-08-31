from __future__ import annotations

import subprocess
from pathlib import Path

from repoatlas.git.blame import blame_context
from repoatlas.git.commits import commit_summary
from repoatlas.git.diffs import diff
from repoatlas.git.history import file_history


class GitCutoffViolation(PermissionError):
    """Raised when a Git query would cross the frozen benchmark cutoff."""


class GitTools:
    """Read-only Git tools constrained to history visible at ``base_commit``."""

    def __init__(self, repo: str | Path, base_commit: str = "HEAD"):
        self.repo = Path(repo).resolve()
        self.base = self._resolve(base_commit)

    def _resolve(self, commit: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", f"{commit}^{{commit}}"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()

    def _assert_visible(self, commit: str) -> str:
        resolved = self._resolve(commit)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "merge-base",
                "--is-ancestor",
                resolved,
                self.base,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            raise GitCutoffViolation(
                f"Commit {resolved[:12]} is not visible at frozen base {self.base[:12]}."
            )
        return resolved

    def get_file_history(self, path: str):
        return file_history(self.repo, path, self.base)

    def get_symbol_history(self, path: str):
        # Conservative MVP: symbol history is file history at the frozen cutoff.
        # Callers can filter these commits using symbol blame/context evidence.
        return self.get_file_history(path)

    def get_commit_summary(self, commit: str):
        return commit_summary(self.repo, self._assert_visible(commit))

    def get_blame_context(self, path: str, start: int, end: int):
        return blame_context(self.repo, path, start, end, self.base)

    def get_diff(self, a: str, b: str):
        return diff(self.repo, self._assert_visible(a), self._assert_visible(b))
