from pathlib import Path

from repoatlas.patching.application import apply_unified_patch, workspace_diff
from repoatlas.sandbox.manager import create_workspace


class WorkspaceTools:
    def __init__(self, source: Path, workspaces: Path = Path("workspaces")):
        self.source = source
        self.workspaces = workspaces

    def create_workspace(self, task_id):
        return create_workspace(self.source, self.workspaces / task_id)

    def apply_patch(self, workspace, patch):
        return apply_unified_patch(workspace, patch)

    def read_workspace_diff(self, workspace):
        return workspace_diff(workspace)
