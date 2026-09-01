from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repoatlas.core.constants import PermissionLevel
from repoatlas.patching.application import (
    workspace_diff,
)
from repoatlas.patching.planner import (
    deterministic_patch_plan,
)
from repoatlas.patching.structured_edits import (
    apply_structured_edits,
    generate_structured_edits,
)
from repoatlas.patching.verifier import (
    verify_diff,
)
from repoatlas.sandbox.manager import (
    SandboxManager,
    create_workspace,
)
from repoatlas.security.permissions import (
    authorize,
)
from repoatlas.tools.registry import (
    get_tool_policy,
)

_DIFF_FILE = re.compile(r"(?m)^diff --git a/(.+?) b/")


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


def _changed_files(
    diff_text: str,
) -> list[str]:
    return list(dict.fromkeys(_DIFF_FILE.findall(diff_text)))


def _is_test_file(
    path: str,
) -> bool:
    name = Path(path).name

    return path.startswith(
        (
            "tests/",
            "test/",
        )
    ) or name.startswith("test_")


class SafePatchWorkflow:
    """Bounded isolated V6 patch workflow.

    The LLM generates structured exact search/replace edits.

    RepoAtlas deterministically applies those edits inside an isolated
    workspace and then derives the real Git diff from the workspace.

    The original repository is never modified.
    """

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

        self.max_attempts = max(
            1,
            min(
                max_attempts,
                2,
            ),
        )

    @staticmethod
    def _restore_workspace(
        workspace: Path,
    ) -> None:
        subprocess.run(
            [
                "git",
                "reset",
                "--hard",
                "HEAD",
            ],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            [
                "git",
                "clean",
                "-fd",
            ],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

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

        authorize(
            get_tool_policy("workspace.create"),
            PermissionLevel.WRITE,
        )

        authorize(
            get_tool_policy("workspace.apply_patch"),
            PermissionLevel.WRITE,
        )

        authorize(
            get_tool_policy("tests.run"),
            PermissionLevel.WRITE,
        )

        plan = deterministic_patch_plan(
            task_id,
            task,
            candidates,
        )

        if not plan.files:
            raise ValueError("No evidence-backed files are available for a patch plan.")

        expected_files = list(dict.fromkeys(item.file_path for item in plan.files))

        workspace = create_workspace(
            self.source_snapshot,
            self.workspaces_root / task_id,
        )

        apply_result: dict[
            str,
            Any,
        ] = {
            "ok": False,
            "strategy": ("evidence_line_range_edits"),
            "applied_edits": 0,
            "changed_files": [],
            "stderr": "not attempted",
        }

        test_result: dict[str, Any] | None = None

        quality_results: list[dict[str, Any]] = []

        verification = verify_diff("")

        previous_failure = ""

        completed_attempts = 0

        for attempt in range(
            1,
            self.max_attempts + 1,
        ):
            completed_attempts = attempt

            if attempt > 1:
                self._restore_workspace(workspace)

            repair_context = evidence

            if previous_failure:
                repair_context += (
                    "\n\n"
                    "PREVIOUS STRUCTURED EDIT "
                    "ATTEMPT FAILED.\n"
                    "Correct the following problem "
                    "in this attempt:\n"
                    f"{previous_failure[-12000:]}\n\n"
                    "Copy search text exactly from "
                    "the supplied repository source "
                    "evidence."
                )

            if test_result and not test_result.get("ok"):
                repair_context += f"\n\nPREVIOUS FOCUSED TEST FAILURE:\n{str(test_result)[-12000:]}"

            try:
                edits = generate_structured_edits(
                    provider=self.provider,
                    task=task,
                    plan=plan,
                    evidence=repair_context,
                )
            except ValueError as exc:
                apply_result = {
                    "ok": False,
                    "strategy": ("evidence_line_range_edits"),
                    "applied_edits": 0,
                    "changed_files": [],
                    "stderr": (f"structured edit generation failed: {exc}"),
                }

                previous_failure = apply_result["stderr"]

                continue

            apply_result = apply_structured_edits(
                workspace=workspace,
                edits=edits,
                allowed_files=(expected_files),
            )

            if not apply_result.get("ok"):
                previous_failure = str(
                    apply_result.get(
                        "stderr",
                        "structured edit application failed",
                    )
                )

                continue

            diff_text = workspace_diff(workspace)

            changed_files = _changed_files(diff_text)

            if not changed_files:
                previous_failure = "Structured edits produced no Git diff."

                continue

            test_result = self.sandbox.run_pytest(
                workspace,
                selected_tests or [],
            )

            quality_results = []

            changed_python = [path for path in changed_files if path.endswith(".py")]

            for path in changed_python:
                result = self.sandbox.run_ruff(
                    workspace,
                    path,
                )

                result = {
                    **result,
                    "tool": "ruff",
                    "target": path,
                }

                quality_results.append(result)

            changed_source_python = [path for path in changed_python if not _is_test_file(path)]

            for path in changed_source_python:
                result = self.sandbox.run_bandit(
                    workspace,
                    path,
                )

                result = {
                    **result,
                    "tool": "bandit",
                    "target": path,
                }

                quality_results.append(result)

            verification = verify_diff(
                diff_text,
                test_result=test_result,
                quality_results=(quality_results),
                expected_files=(expected_files),
            )

            if verification.passed:
                return SafePatchResult(
                    task_id=task_id,
                    workspace=str(workspace),
                    plan=plan.model_dump(),
                    patch=diff_text,
                    apply_result=(apply_result),
                    test_result=(test_result),
                    quality_results=(quality_results),
                    verification=(verification.model_dump()),
                    attempts=attempt,
                )

            previous_failure = f"Verification failed:\n{verification.model_dump()}"

        final_diff = workspace_diff(workspace)

        verification = verify_diff(
            final_diff,
            test_result=test_result,
            quality_results=(quality_results),
            expected_files=(expected_files),
        )

        return SafePatchResult(
            task_id=task_id,
            workspace=str(workspace),
            plan=plan.model_dump(),
            patch=final_diff,
            apply_result=(apply_result),
            test_result=(test_result),
            quality_results=(quality_results),
            verification=(verification.model_dump()),
            attempts=completed_attempts,
        )
