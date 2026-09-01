from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from repoatlas.patching.workflow import (
    SafePatchWorkflow,
)

_SOURCE_REF = re.compile(r"\[SRC:\s*(.+?):L(\d+)-L(\d+)\]")


def write_tools_enabled() -> bool:
    """Explicit opt-in only."""

    return (
        os.getenv(
            "ENABLE_WRITE_TOOLS",
            "",
        )
        .strip()
        .lower()
        == "true"
    )


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


def _tree_digest(
    root: Path,
) -> str:
    """Stable digest proving source snapshot immutability."""

    digest = hashlib.sha256()

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)

        if ".git" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue

        digest.update(str(relative).encode("utf-8"))

        digest.update(path.read_bytes())

    return digest.hexdigest()


def _evidence_strings(
    hit: Any,
) -> list[str]:
    value = getattr(
        hit,
        "evidence",
        [],
    )

    if isinstance(
        value,
        str,
    ):
        return [value]

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [str(item) for item in value]

    return [str(value)]


def _source_reference(
    hit: Any,
) -> tuple[str, int, int] | None:
    for item in _evidence_strings(hit):
        match = _SOURCE_REF.search(item)

        if match:
            return (
                match.group(1),
                int(match.group(2)),
                int(match.group(3)),
            )

    return None


def _source_excerpt(
    repo: Path,
    file_path: str,
    start: int,
    end: int,
    *,
    padding: int = 5,
    max_lines: int = 100,
) -> str:
    candidate = (repo / file_path).resolve()

    try:
        candidate.relative_to(repo)
    except ValueError:
        return "[unsafe path rejected]"

    if not candidate.is_file():
        return "[source file unavailable]"

    lines = candidate.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    lower = max(
        1,
        start - padding,
    )

    upper = min(
        len(lines),
        end + padding,
    )

    if upper - lower + 1 > max_lines:
        upper = lower + max_lines - 1

    return "\n".join(
        f"{number:>5}: {lines[number - 1]}"
        for number in range(
            lower,
            upper + 1,
        )
    )


def build_patch_evidence(
    *,
    repo: Path,
    task: str,
    direct_hits: list[Any],
    v5_report: dict[str, Any],
) -> str:
    """Build patch context only from runtime repository evidence."""

    sections = [
        "TASK:",
        task,
        "",
        "V5 INVESTIGATION REPORT:",
        str(
            v5_report.get(
                "investigation_report",
                "",
            )
        ),
        "",
        "REPOSITORY SOURCE EVIDENCE:",
    ]

    for index, hit in enumerate(
        direct_hits[:8],
        start=1,
    ):
        sections.extend(
            [
                "",
                (f"[C{index}] {hit.file_path}::{hit.qualified_symbol}"),
            ]
        )

        reference = _source_reference(hit)

        if reference is None:
            sections.append("Evidence metadata: " + " | ".join(_evidence_strings(hit)))
            continue

        (
            file_path,
            start,
            end,
        ) = reference

        sections.extend(
            [
                (f"Source: {file_path}:L{start}-L{end}"),
                "```python",
                _source_excerpt(
                    repo,
                    file_path,
                    start,
                    end,
                ),
                "```",
            ]
        )

    sections.extend(
        [
            "",
            "SAFETY REQUIREMENTS:",
            ("- Modify only evidence-backed files from the patch plan."),
            ("- Produce only a Git-style unified diff."),
            ("- Keep the change minimal and focused on the stated task."),
            ("- Do not modify repository configuration unless required."),
            ("- Add or update a focused test when appropriate."),
        ]
    )

    return "\n".join(sections)


class V6SafeCodingAgent:
    """RepoAtlas V6 safe coding agent.

    Write access requires ENABLE_WRITE_TOOLS=true.
    The original frozen repository is never modified.
    """

    def __init__(
        self,
        *,
        source_snapshot: Path,
        runtime: dict[str, Any],
        provider: Any,
        v5_report: dict[str, Any],
        workspaces_root: Path = Path("workspaces"),
    ) -> None:
        self.source_snapshot = source_snapshot.resolve()

        self.runtime = runtime
        self.provider = provider
        self.v5_report = v5_report

        self.workspaces_root = workspaces_root.resolve()

    def _base_commit(
        self,
    ) -> str | None:
        marker = self.source_snapshot / ".repoatlas_base_commit"

        if not marker.exists():
            return None

        return marker.read_text(encoding="utf-8").strip()

    def _validate_v5_binding(
        self,
    ) -> None:
        actual = self._base_commit()

        expected = self.v5_report.get("base_commit")

        if actual and expected and actual != expected:
            raise ValueError("V5 evidence BASE does not match V6 source snapshot.")

    def run(
        self,
        task: str,
    ) -> dict[str, Any]:
        if not write_tools_enabled():
            raise PermissionError(
                "V6 write mode denied. "
                "Set ENABLE_WRITE_TOOLS=true "
                "for an explicit isolated "
                "patch attempt."
            )

        self._validate_v5_binding()

        direct_hits = list(self.runtime["hybrid"].search(task))[:12]

        if not direct_hits:
            raise RuntimeError("No V2 evidence available for safe patch planning.")

        selected_tests: list[str] = []

        for hit in direct_hits:
            path = hit.file_path

            if _is_test_file(path) and path not in selected_tests:
                selected_tests.append(path)

            if len(selected_tests) >= 1:
                break

        if not selected_tests:
            for path in self.v5_report.get(
                "related_tests",
                [],
            ):
                if path not in selected_tests:
                    selected_tests.append(path)

                if len(selected_tests) >= 1:
                    break

        evidence = build_patch_evidence(
            repo=self.source_snapshot,
            task=task,
            direct_hits=direct_hits,
            v5_report=self.v5_report,
        )

        source_before = _tree_digest(self.source_snapshot)

        task_id = "v6-" + uuid.uuid4().hex[:12]

        workflow = SafePatchWorkflow(
            source_snapshot=(self.source_snapshot),
            workspaces_root=(self.workspaces_root),
            provider=self.provider,
            max_attempts=2,
        )

        result = workflow.run(
            task_id=task_id,
            task=task,
            candidates=direct_hits,
            evidence=evidence,
            selected_tests=(selected_tests),
            allow_write=True,
        )

        source_after = _tree_digest(self.source_snapshot)

        original_unchanged = source_before == source_after

        return {
            "agent_version": "V6",
            "task_id": task_id,
            "task": task,
            "base_commit": (self._base_commit()),
            "write_gate": {
                "environment_variable": ("ENABLE_WRITE_TOOLS"),
                "explicitly_enabled": True,
            },
            "retrieval": {
                "primary": ("V2_BM25_BGE_M3_RRF"),
                "candidate_count": len(direct_hits),
            },
            "selected_tests": (selected_tests),
            "workspace": (result.workspace),
            "attempts": (result.attempts),
            "apply_result": (result.apply_result),
            "test_result": (result.test_result),
            "quality_results": (result.quality_results),
            "verification": (result.verification),
            "patch": (result.patch),
            "original_snapshot": {
                "before_sha256": (source_before),
                "after_sha256": (source_after),
                "unchanged": (original_unchanged),
            },
            "safety": {
                "writes_target": ("isolated_workspace_only"),
                "original_repository_modified": (not original_unchanged),
                "max_attempts": 2,
            },
        }


def serialize_v6_result(
    result: dict[str, Any],
) -> str:
    return json.dumps(
        result,
        indent=2,
    )
