import shutil
import subprocess
from pathlib import Path

from repoatlas.sandbox.docker import DockerSandbox


def create_workspace(source: Path, dest: Path) -> Path:
    """Create an isolated copy and initialize a local baseline Git commit.

    The original repository is never modified. Initializing a fresh Git repository in
    the copied workspace gives RepoAtlas a deterministic local diff even when the
    source is a frozen snapshot without `.git` metadata.
    """
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
    subprocess.run(["git", "init"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "repoatlas@local.invalid"], cwd=dest, check=True)
    subprocess.run(["git", "config", "user.name", "RepoAtlas Workspace"], cwd=dest, check=True)
    subprocess.run(["git", "add", "."], cwd=dest, check=True)
    subprocess.run(
        ["git", "commit", "-m", "RepoAtlas baseline"], cwd=dest, check=True, capture_output=True
    )
    return dest


class SandboxManager:
    def __init__(self, docker: DockerSandbox | None = None):
        self.docker = docker or DockerSandbox()

    def run_pytest(self, workspace: Path, targets: list[str]):
        return self.docker.run(workspace, ["python", "-m", "pytest", "-q", *targets])

    def run_ruff(self, workspace: Path, target: str = "."):
        return self.docker.run(workspace, ["ruff", "check", target])

    def run_mypy(self, workspace: Path, target: str = "."):
        return self.docker.run(workspace, ["mypy", target])

    def run_bandit(self, workspace: Path, target: str = "."):
        return self.docker.run(workspace, ["bandit", "-q", "-r", target])
