from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from repoatlas.agents.v6 import (
    V6SafeCodingAgent,
    serialize_v6_result,
)
from repoatlas.llm.local_provider import (
    TransformersCoderProvider,
)
from repoatlas.pipeline import (
    build_runtime,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=("Run RepoAtlas V6 safe coding agent."))

    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--task",
        required=True,
    )

    parser.add_argument(
        "--v5-report",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-8B",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--workspaces-root",
        type=Path,
        default=Path("workspaces"),
    )

    args = parser.parse_args()

    enabled = (
        os.getenv(
            "ENABLE_WRITE_TOOLS",
            "",
        )
        .strip()
        .lower()
        == "true"
    )

    if not enabled:
        print(
            json.dumps(
                {
                    "agent_version": "V6",
                    "status": ("WRITE_MODE_DENIED"),
                    "reason": ("ENABLE_WRITE_TOOLS is not true."),
                    "original_repository_modified": False,
                },
                indent=2,
            )
        )

        raise SystemExit(2)

    v5_report = json.loads(args.v5_report.read_text(encoding="utf-8"))

    print("Building frozen V2 runtime...")

    runtime = build_runtime(
        args.repo.resolve(),
        embedding="bge",
        reranker="heuristic",
    )

    print("Loading local Qwen3-8B patch provider...")

    provider = TransformersCoderProvider(
        model=args.model,
    )

    agent = V6SafeCodingAgent(
        source_snapshot=(args.repo),
        runtime=runtime,
        provider=provider,
        v5_report=v5_report,
        workspaces_root=(args.workspaces_root),
    )

    print("Running isolated V6 patch workflow...")

    result = agent.run(args.task)

    payload = serialize_v6_result(result)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        payload + "\n",
        encoding="utf-8",
    )

    print()
    print(payload)
    print()
    print(
        "Saved:",
        args.output,
    )

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

    if verification_passed and original_unchanged:
        print()
        print("REAL V6 SAFE PATCH: PASS")
        raise SystemExit(0)

    print()
    print("REAL V6 SAFE PATCH: COMPLETED WITH FAILED VERIFICATION")

    raise SystemExit(1)


if __name__ == "__main__":
    main()
