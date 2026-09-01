from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--result",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--case",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))

    case = json.loads(args.case.read_text(encoding="utf-8"))

    patch = result.get(
        "patch",
        "",
    )

    changed_files = sorted(
        set(
            re.findall(
                r"(?m)^diff --git a/(.+?) b/",
                patch,
            )
        )
    )

    historical_files = sorted(
        case.get(
            "expected_changed_files",
            [],
        )
    )

    overlap = sorted(set(changed_files) & set(historical_files))

    verification_passed = bool(
        result.get(
            "verification",
            {},
        ).get(
            "passed",
            False,
        )
    )

    original_unchanged = bool(
        result.get(
            "original_snapshot",
            {},
        ).get(
            "unchanged",
            False,
        )
    )

    print()
    print("=== V6 HISTORICAL PROOF ===")
    print()

    print(
        "Attempts:",
        result.get("attempts"),
    )

    print(
        "Focused tests:",
        result.get(
            "selected_tests",
            [],
        ),
    )

    print(
        "Generated changed files:",
        changed_files,
    )

    print(
        "Historical changed files:",
        historical_files,
    )

    print(
        "Historical file overlap:",
        overlap,
    )

    print(
        "Verification passed:",
        verification_passed,
    )

    print(
        "Original snapshot unchanged:",
        original_unchanged,
    )

    if not original_unchanged:
        raise SystemExit("Original snapshot changed. STOP.")

    print()
    print("V6 ORIGINAL-SNAPSHOT SAFETY: PASS")

    if verification_passed:
        print("V6 WORKFLOW VERIFICATION: PASS")
    else:
        print("V6 WORKFLOW VERIFICATION: FAILED")


if __name__ == "__main__":
    main()
