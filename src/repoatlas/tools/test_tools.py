from pathlib import Path

from repoatlas.sandbox.manager import SandboxManager


class TestTools:
    def __init__(self, workspace: Path, sandbox: SandboxManager):
        self.workspace = workspace
        self.sandbox = sandbox

    def discover_tests(self):
        return [p.relative_to(self.workspace).as_posix() for p in self.workspace.rglob("test*.py")]

    def run_selected_tests(self, targets: list[str]):
        return self.sandbox.run_pytest(self.workspace, targets)

    def run_test_file(self, target: str):
        return self.run_selected_tests([target])

    def run_full_test_suite(self):
        return self.run_selected_tests([])
