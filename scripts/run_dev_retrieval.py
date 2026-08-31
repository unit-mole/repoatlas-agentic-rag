from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--manifest",
        default="benchmark/dev_cases.json",
    )

    parser.add_argument(
        "--graph-hops",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    manifest = Path(args.manifest)

    cases = json.loads(manifest.read_text(encoding="utf-8"))

    if not cases:
        raise RuntimeError("DEV benchmark manifest is empty.")

    output_dir = Path("reports/experiments/dev")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print(f"Running V0-V4 on {len(cases)} historical DEV cases.")
    print("Embedding : BGE-M3")
    print("Reranker  : BGE reranker v2 m3")
    print(
        "Graph hops:",
        args.graph_hops,
    )

    for index, item in enumerate(
        cases,
        start=1,
    ):
        case_id = item["case_id"]

        snapshot = Path("data/snapshots") / case_id

        case_path = Path("benchmark/cases") / f"{case_id}.json"

        output = output_dir / f"{case_id}-v0-v4.json"

        print()
        print("=" * 72)
        print(f"[{index}/{len(cases)}] {case_id}")
        print("=" * 72)

        command = [
            sys.executable,
            "-m",
            "scripts.evaluate_retrieval",
            "--repo",
            str(snapshot),
            "--case",
            str(case_path),
            "--embedding",
            "bge",
            "--reranker",
            "bge",
            "--graph-hops",
            str(args.graph_hops),
            "--output",
            str(output),
        ]

        subprocess.run(
            command,
            check=True,
        )

    print()
    print("MULTI-CASE V0-V4 DEV RUN: PASS")


if __name__ == "__main__":
    main()
