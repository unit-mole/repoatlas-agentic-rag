class QualityTools:
    def __init__(self, workspace, sandbox):
        self.workspace = workspace
        self.sandbox = sandbox

    def run_linter(self, target="."):
        return self.sandbox.run_ruff(self.workspace, target)

    def run_type_checker(self, target="."):
        return self.sandbox.run_mypy(self.workspace, target)

    def run_static_analysis(self, target="."):
        return self.sandbox.run_bandit(self.workspace, target)
