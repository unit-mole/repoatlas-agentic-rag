from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_EVIDENCE_RANGE = re.compile(r"(?m)^Source:\s+(.+?):L(\d+)-L(\d+)\s*$")


@dataclass(frozen=True)
class StructuredEdit:
    file_path: str
    start_line: int
    end_line: int
    replacement: str
    reason: str = ""


SYSTEM_PROMPT = """\
You are the RepoAtlas V6 patch-generation component.

You are operating on a frozen repository snapshot.

Do NOT generate a unified diff.
Do NOT generate search/replace strings.

Return only one JSON object:

{
  "edits": [
    {
      "file_path": "relative/path.py",
      "start_line": 10,
      "end_line": 14,
      "replacement": "complete replacement text",
      "reason": "short explanation"
    }
  ]
}

Rules:

1. Modify only files listed in APPROVED FILES.
2. Use only line ranges shown in ALLOWED EVIDENCE RANGES.
3. Line numbers are 1-based and inclusive.
4. Each edit replaces start_line through end_line.
5. Keep edits minimal.
6. Preserve Python indentation.
7. Do not invent files, APIs, functions, or repository behavior.
8. Do not modify CI, dependency locks, or configuration unless approved.
9. Do not disable, delete, skip, or weaken tests.
10. A source-only edit is acceptable when the supplied focused tests
    already verify the relevant behavior.
11. Add or update a test only when the evidence supports doing so.
12. Return no Markdown and no prose outside the JSON object.
13. If no safe evidence-backed edit is possible, return:
    {"edits": []}
"""


def _extract_json_object(
    text: str,
) -> dict[str, Any]:
    start = text.find("{")

    if start < 0:
        raise ValueError("Model response did not contain a JSON object.")

    decoder = json.JSONDecoder()

    try:
        value, _ = decoder.raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response contained invalid JSON: {exc}") from exc

    if not isinstance(
        value,
        dict,
    ):
        raise TypeError("Structured patch payload must be a JSON object.")

    return value


def _safe_path(
    value: str,
) -> str:
    path = Path(value)

    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe edit path: {value!r}")

    normalized = path.as_posix()

    if not normalized:
        raise ValueError("Edit path is empty.")

    return normalized


def _line_number(
    value: Any,
    *,
    field: str,
    edit_index: int,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        raise TypeError(f"Edit {edit_index} {field} must be an integer.")

    if isinstance(
        value,
        int,
    ):
        return value

    if (
        isinstance(
            value,
            str,
        )
        and value.isdigit()
    ):
        return int(value)

    raise TypeError(f"Edit {edit_index} {field} must be an integer.")


def evidence_ranges(
    evidence: str,
) -> dict[
    str,
    list[tuple[int, int]],
]:
    ranges: dict[
        str,
        list[tuple[int, int]],
    ] = {}

    for match in _EVIDENCE_RANGE.finditer(evidence):
        file_path = _safe_path(match.group(1).strip())

        start = int(match.group(2))

        end = int(match.group(3))

        ranges.setdefault(
            file_path,
            [],
        ).append(
            (
                start,
                end,
            )
        )

    return ranges


def _inside_allowed_range(
    *,
    file_path: str,
    start_line: int,
    end_line: int,
    ranges: dict[
        str,
        list[tuple[int, int]],
    ],
) -> bool:
    return any(
        start_line >= allowed_start and end_line <= allowed_end
        for (
            allowed_start,
            allowed_end,
        ) in ranges.get(
            file_path,
            [],
        )
    )


def extract_structured_edits(
    text: str,
    *,
    approved_files: set[str],
    allowed_ranges: dict[
        str,
        list[tuple[int, int]],
    ],
    max_edits: int = 6,
    max_span_lines: int = 100,
) -> list[StructuredEdit]:
    payload = _extract_json_object(text)

    raw_edits = payload.get("edits")

    if not isinstance(
        raw_edits,
        list,
    ):
        raise TypeError("Structured patch JSON must contain an edits list.")

    if not raw_edits:
        raise ValueError("Model returned no structured edits.")

    if len(raw_edits) > max_edits:
        raise ValueError(f"Structured patch exceeded the maximum of {max_edits} edits.")

    approved = {_safe_path(path) for path in approved_files}

    edits: list[StructuredEdit] = []

    for index, raw in enumerate(
        raw_edits,
        start=1,
    ):
        if not isinstance(
            raw,
            dict,
        ):
            raise TypeError(f"Edit {index} must be an object.")

        file_value = raw.get("file_path")

        if not isinstance(
            file_value,
            str,
        ):
            raise TypeError(f"Edit {index} file_path must be a string.")

        file_path = _safe_path(file_value)

        if file_path not in approved:
            raise ValueError(f"Edit {index} targets unapproved file: {file_path}")

        start_line = _line_number(
            raw.get("start_line"),
            field="start_line",
            edit_index=index,
        )

        end_line = _line_number(
            raw.get("end_line"),
            field="end_line",
            edit_index=index,
        )

        if start_line < 1 or end_line < start_line:
            raise ValueError(f"Edit {index} contains an invalid line range.")

        span = end_line - start_line + 1

        if span > max_span_lines:
            raise ValueError(f"Edit {index} exceeds {max_span_lines} lines.")

        if not _inside_allowed_range(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            ranges=allowed_ranges,
        ):
            raise ValueError(
                f"Edit {index} range "
                f"{file_path}:"
                f"L{start_line}-L{end_line} "
                "is outside retrieved evidence."
            )

        replacement = raw.get("replacement")

        if not isinstance(
            replacement,
            str,
        ):
            raise TypeError(f"Edit {index} replacement must be a string.")

        reason = raw.get(
            "reason",
            "",
        )

        if not isinstance(
            reason,
            str,
        ):
            reason = str(reason)

        edits.append(
            StructuredEdit(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                replacement=replacement,
                reason=reason,
            )
        )

    return edits


def generate_structured_edits(
    *,
    provider,
    task: str,
    plan,
    evidence: str,
) -> list[StructuredEdit]:
    approved_files = {item.file_path for item in plan.files}

    ranges = evidence_ranges(evidence)

    if not ranges:
        raise ValueError("No source line ranges were available in repository evidence.")

    approved_text = "\n".join(f"- {path}" for path in sorted(approved_files))

    range_text = "\n".join(
        (
            f"- {path}: "
            + ", ".join(
                f"L{start}-L{end}"
                for (
                    start,
                    end,
                ) in spans
            )
        )
        for path, spans in sorted(ranges.items())
        if path in approved_files
    )

    user_prompt = (
        "TASK:\n"
        f"{task}\n\n"
        "APPROVED FILES:\n"
        f"{approved_text}\n\n"
        "ALLOWED EVIDENCE RANGES:\n"
        f"{range_text}\n\n"
        "PATCH PLAN:\n"
        f"{plan.model_dump_json(indent=2)}\n\n"
        "REPOSITORY EVIDENCE:\n"
        f"{evidence}\n\n"
        "Return the JSON edit object now."
    )

    response = provider.complete(
        SYSTEM_PROMPT,
        user_prompt,
        temperature=0.0,
        max_tokens=4096,
    )

    return extract_structured_edits(
        response,
        approved_files=(approved_files),
        allowed_ranges=ranges,
    )


def _validate_non_overlapping(
    edits: list[StructuredEdit],
) -> None:
    by_file: dict[
        str,
        list[StructuredEdit],
    ] = {}

    for edit in edits:
        by_file.setdefault(
            edit.file_path,
            [],
        ).append(edit)

    for file_path, items in by_file.items():
        ordered = sorted(
            items,
            key=lambda item: (
                item.start_line,
                item.end_line,
            ),
        )

        for previous, current in itertools.pairwise(ordered):
            if current.start_line <= previous.end_line:
                raise ValueError(
                    "Overlapping edits in "
                    f"{file_path}: "
                    f"{previous.start_line}-"
                    f"{previous.end_line} and "
                    f"{current.start_line}-"
                    f"{current.end_line}."
                )


def apply_structured_edits(
    *,
    workspace: Path,
    edits: list[StructuredEdit],
    allowed_files: list[str],
) -> dict[str, Any]:
    """Apply line-range edits transactionally."""

    if not edits:
        return {
            "ok": False,
            "strategy": ("evidence_line_range_edits"),
            "applied_edits": 0,
            "changed_files": [],
            "stderr": ("No structured edits supplied."),
        }

    try:
        _validate_non_overlapping(edits)
    except ValueError as exc:
        return {
            "ok": False,
            "strategy": ("evidence_line_range_edits"),
            "applied_edits": 0,
            "changed_files": [],
            "stderr": str(exc),
        }

    workspace = workspace.resolve()

    allowed = {_safe_path(path) for path in allowed_files}

    by_file: dict[
        str,
        list[StructuredEdit],
    ] = {}

    for edit in edits:
        if edit.file_path not in allowed:
            return {
                "ok": False,
                "strategy": ("evidence_line_range_edits"),
                "applied_edits": 0,
                "changed_files": [],
                "stderr": (f"Edit targeted a file outside the patch plan: {edit.file_path}"),
            }

        by_file.setdefault(
            edit.file_path,
            [],
        ).append(edit)

    staged: dict[
        str,
        str,
    ] = {}

    for file_path, file_edits in by_file.items():
        target = (workspace / file_path).resolve()

        try:
            target.relative_to(workspace)
        except ValueError:
            return {
                "ok": False,
                "strategy": ("evidence_line_range_edits"),
                "applied_edits": 0,
                "changed_files": [],
                "stderr": (f"Edit escaped workspace: {file_path}"),
            }

        if not target.is_file():
            return {
                "ok": False,
                "strategy": ("evidence_line_range_edits"),
                "applied_edits": 0,
                "changed_files": [],
                "stderr": (f"Edit target does not exist: {file_path}"),
            }

        original = target.read_text(
            encoding="utf-8",
            errors="strict",
        )

        trailing_newline = original.endswith("\n")

        lines = original.splitlines()

        for edit in sorted(
            file_edits,
            key=lambda item: item.start_line,
            reverse=True,
        ):
            if edit.end_line > len(lines):
                return {
                    "ok": False,
                    "strategy": ("evidence_line_range_edits"),
                    "applied_edits": 0,
                    "changed_files": [],
                    "stderr": (
                        "Edit range is outside "
                        f"{file_path}: "
                        f"L{edit.start_line}-"
                        f"L{edit.end_line}; "
                        f"file has {len(lines)} lines."
                    ),
                }

            replacement_lines = edit.replacement.splitlines()

            lines[edit.start_line - 1 : edit.end_line] = replacement_lines

        updated = "\n".join(lines)

        if trailing_newline:
            updated += "\n"

        if updated == original:
            return {
                "ok": False,
                "strategy": ("evidence_line_range_edits"),
                "applied_edits": 0,
                "changed_files": [],
                "stderr": (f"Structured edits produced no change in {file_path}."),
            }

        staged[file_path] = updated

    for file_path, content in staged.items():
        (workspace / file_path).write_text(
            content,
            encoding="utf-8",
        )

    return {
        "ok": True,
        "strategy": ("evidence_line_range_edits"),
        "applied_edits": len(edits),
        "changed_files": sorted(staged),
        "stderr": "",
    }
