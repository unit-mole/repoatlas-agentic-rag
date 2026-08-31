from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repoatlas.core.constants import PermissionLevel
from repoatlas.patching.application import apply_unified_patch, workspace_diff
from repoatlas.patching.generator import generate_patch
from repoatlas.patching.planner import deterministic_patch_plan
from repoatlas.patching.verifier import verify_diff
from repoatlas.sandbox.manager import SandboxManager, create_workspace
from repoatlas.security.permissions import authorize
from repoatlas.tools.registry import get_tool_policy


@dataclass
class SafePatchResult:
    task_id: str
    workspace: str
    plan: dict[str, Any]
    patch: str
    apply_result: dict[str, Any]
    test_result: dict[str, Any] | None
    quality_results: list[dict[str, Any]]
    verification: dict[str, Any]
    attempts: int
    approval_required: bool = True


class SafePatchWorkflow:
    """Bounded local patch workflow. It never edits or pushes the original repository."""

    def __init__(
        self,
        *,
        source_snapshot: Path,
        workspaces_root: Path,
        provider,
        sandbox: SandboxManager | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.source_snapshot = source_snapshot.resolve()
        self.workspaces_root = workspaces_root.resolve()
        self.provider = provider
        self.sandbox = sandbox or SandboxManager()
        self.max_attempts = max(1, min(max_attempts, 2))

    def run(
        self,
        *,
        task_id: str,
        task: str,
        candidates,
        evidence: str,
        selected_tests: list[str] | None = None,
        allow_write: bool = False,
    ) -> SafePatchResult:
        if not allow_write:
            raise PermissionError(
                "Safe patch workflow is disabled. Explicitly enable isolated write mode first."
            )
        authorize(get_tool_policy("workspace.create"), PermissionLevel.WRITE)
        authorize(get_tool_policy("workspace.apply_patch"), PermissionLevel.WRITE)
        authorize(get_tool_policy("tests.run"), PermissionLevel.WRITE)

        plan = deterministic_patch_plan(task_id, task, candidates)
        if not plan.files:
            raise ValueError("No evidence-backed files are available for a patch plan.")
        expected_files = [item.file_path for item in plan.files]
        workspace = create_workspace(self.source_snapshot, self.workspaces_root / task_id)

        patch = ""
        apply_result: dict[str, Any] = {"ok": False, "stderr": "not attempted"}
        test_result: dict[str, Any] | None = None
        quality_results: list[dict[str, Any]] = []
        verification = verify_diff("")

        for attempt in range(1, self.max_attempts + 1):
            # Restore workspace to its frozen baseline before each bounded attempt.
            if attempt > 1:
                import subprocess

                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=workspace,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "clean", "-fd"], cwd=workspace, check=True, capture_output=True
                )

            repair_context = evidence
            if test_result and not test_result.get("ok"):
                repair_context += "\nPrevious focused-test failure:\n" + str(test_result)[-12_000:]
            patch = generate_patch(self.provider, task, plan, repair_context)
            apply_result = apply_unified_patch(workspace, patch)
            if not apply_result.get("ok"):
                continue

            test_result = self.sandbox.run_pytest(workspace, selected_tests or [])
            quality_results = [
                self.sandbox.run_ruff(workspace, "."),
                self.sandbox.run_bandit(workspace, "."),
            ]
            diff_text = workspace_diff(workspace)
            verification = verify_diff(
                diff_text,
                test_result=test_result,
                quality_results=quality_results,
                expected_files=expected_files,
            )
            if verification.passed:
                return SafePatchResult(
                    task_id=task_id,
                    workspace=str(workspace),
                    plan=plan.model_dump(),
                    patch=diff_text,
                    apply_result=apply_result,
                    test_result=test_result,
                    quality_results=quality_results,
                    verification=verification.model_dump(),
                    attempts=attempt,
                )

        diff_text = workspace_diff(workspace)
        verification = verify_diff(
            diff_text,
            test_result=test_result,
            quality_results=quality_results,
            expected_files=expected_files,
        )
        return SafePatchResult(
            task_id=task_id,
            workspace=str(workspace),
            plan=plan.model_dump(),
            patch=diff_text,
            apply_result=apply_result,
            test_result=test_result,
            quality_results=quality_results,
            verification=verification.model_dump(),
            attempts=self.max_attempts,
        )
