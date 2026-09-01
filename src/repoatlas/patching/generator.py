from __future__ import annotations

import re

from repoatlas.llm.prompts import PATCH, SYSTEM

_DIFF_START = re.compile(r"(?m)^diff --git ")

_HUNK_HEADER = re.compile(
    r"^@@ "
    r"-(?P<old_start>\d+)"
    r"(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)"
    r"(?:,(?P<new_count>\d+))? "
    r"@@(?P<tail>.*)$"
)


def _format_range(
    start: int,
    count: int,
) -> str:
    if count == 1:
        return str(start)

    return f"{start},{count}"


def _normalize_hunks(
    diff: str,
) -> str:
    """Recount generated unified-diff hunks.

    LLMs occasionally emit correct hunk bodies but stale line counts in
    the @@ header. Git then reports a corrupt patch.

    This function does not invent patch content. It only recalculates
    old/new hunk counts from the body that the model already produced.
    """

    lines = diff.splitlines()

    normalized: list[str] = []

    index = 0

    while index < len(lines):
        line = lines[index]

        if not line.startswith("@@ "):
            normalized.append(line)
            index += 1
            continue

        match = _HUNK_HEADER.match(line)

        if match is None:
            raise ValueError(f"Malformed unified-diff hunk header: {line!r}")

        body: list[str] = []

        cursor = index + 1

        while cursor < len(lines):
            candidate = lines[cursor]

            if candidate.startswith(("@@ ", "diff --git ")):
                break

            # LLMs sometimes emit a completely empty line for an empty
            # context line. Unified diff requires the leading space.
            if candidate == "":
                candidate = " "

            if not candidate.startswith(
                (
                    " ",
                    "+",
                    "-",
                    "\\",
                )
            ):
                raise ValueError(f"Malformed unified-diff hunk body line: {candidate!r}")

            body.append(candidate)
            cursor += 1

        if not body:
            raise ValueError("Unified-diff hunk contains no body.")

        old_count = sum(
            1
            for item in body
            if item.startswith(
                (
                    " ",
                    "-",
                )
            )
        )

        new_count = sum(
            1
            for item in body
            if item.startswith(
                (
                    " ",
                    "+",
                )
            )
        )

        old_start = int(match.group("old_start"))

        new_start = int(match.group("new_start"))

        tail = match.group("tail")

        normalized.append(
            "@@ "
            f"-{_format_range(old_start, old_count)} "
            f"+{_format_range(new_start, new_count)} "
            f"@@{tail}"
        )

        normalized.extend(body)

        index = cursor

    return "\n".join(normalized).rstrip() + "\n"


def _validate_diff_structure(
    diff: str,
) -> None:
    """Reject obviously incomplete Git diffs before application."""

    sections = diff.split("diff --git ")

    actual_sections = [section for section in sections if section.strip()]

    if not actual_sections:
        raise ValueError("Generated patch contains no Git diff section.")

    for number, section in enumerate(
        actual_sections,
        start=1,
    ):
        section_lines = section.splitlines()

        if not section_lines:
            raise ValueError(f"Diff section {number} is empty.")

        has_old_header = any(line.startswith("--- ") for line in section_lines)

        has_new_header = any(line.startswith("+++ ") for line in section_lines)

        has_hunk = any(line.startswith("@@ ") for line in section_lines)

        if not (has_old_header and has_new_header and has_hunk):
            raise ValueError(f"Incomplete Git diff section {number}: expected ---/+++/@@ markers.")


def extract_unified_diff(
    text: str,
) -> str:
    """Extract, normalize, and validate a Git-style unified diff."""

    match = _DIFF_START.search(text)

    if match is None:
        raise ValueError("Model response did not contain a Git-style unified diff.")

    diff = text[match.start() :].strip()

    # Remove the closing Markdown fence when the model wraps the diff.
    if "```" in diff:
        diff = diff.split(
            "```",
            1,
        )[0].rstrip()

    diff = _normalize_hunks(diff)

    _validate_diff_structure(diff)

    return diff


def generate_patch(
    provider,
    task,
    plan,
    evidence,
):
    response = provider.complete(
        SYSTEM,
        PATCH.format(
            task=task,
            plan=plan.model_dump_json(indent=2),
            evidence=evidence,
        ),
        temperature=0.1,
        max_tokens=4096,
    )

    return extract_unified_diff(response)
