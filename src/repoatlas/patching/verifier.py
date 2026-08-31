from __future__ import annotations

import re

from repoatlas.schemas.patches import VerificationResult

FORBIDDEN = (
    "pytest.skip",
    "@pytest.mark.skip",
    "assert True",
    "# noqa",
    "# type: ignore",
)
_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)


def changed_files_from_diff(diff_text: str) -> list[str]:
    return list(dict.fromkeys(match.group(2) for match in _DIFF_FILE_RE.finditer(diff_text)))


def verify_diff(
    diff_text: str,
    test_result: dict | None = None,
    quality_results: list[dict] | None = None,
    expected_files: list[str] | None = None,
):
    changed = changed_files_from_diff(diff_text)
    checks = {
        "non_empty": bool(diff_text.strip()),
        "no_obvious_test_suppression": not any(token in diff_text for token in FORBIDDEN),
    }
    notes: list[str] = []
    if expected_files is not None:
        allowed = set(expected_files)
        checks["expected_file_scope"] = bool(changed) and set(changed).issubset(allowed)
        if not checks["expected_file_scope"]:
            notes.append(f"Changed files outside approved plan: {sorted(set(changed) - allowed)}")
    if test_result is not None:
        checks["tests_pass"] = bool(test_result.get("ok"))
    if quality_results:
        checks["quality_pass"] = all(result.get("ok") for result in quality_results)
    return VerificationResult(passed=all(checks.values()), checks=checks, notes=notes)
