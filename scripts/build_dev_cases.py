from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo",
        default="data/repositories/httpx",
    )

    parser.add_argument(
        "--manifest",
        default="benchmark/dev_cases.json",
    )

    args = parser.parse_args()

    repo = Path(args.repo)
    manifest_path = Path(args.manifest)

    cases = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not cases:
        raise RuntimeError("DEV benchmark manifest is empty.")

    print(f"Building {len(cases)} DEV historical cases...")

    for item in cases:
        case_id = item["case_id"]

        print()
        print("=" * 72)
        print(case_id)
        print("=" * 72)

        command = [
            sys.executable,
            "-m",
            "scripts.build_historical_case",
            "--repo",
            str(repo),
            "--repository-name",
            "httpx",
            "--fix-commit",
            item["fix_commit"],
            "--issue-text",
            item["issue_text"],
            "--case-id",
            case_id,
            "--split",
            "dev",
            "--difficulty",
            item["difficulty"],
            "--category",
            item["category"],
        ]

        subprocess.run(
            command,
            check=True,
        )

    print()
    print("DEV HISTORICAL CASE BUILD: PASS")


if __name__ == "__main__":
    main()
