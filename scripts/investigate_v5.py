from __future__ import annotations

import argparse
import json
from pathlib import Path

from repoatlas.agents.v5 import (
    V5InvestigationAgent,
)
from repoatlas.llm.local_provider import (
    TransformersCoderProvider,
)
from repoatlas.pipeline import build_runtime


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run RepoAtlas V5 evidence-backed "
            "repository investigation."
        )
    )

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
        "--model",
        default="Qwen/Qwen3-8B",
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    args = parser.parse_args()

    repo = args.repo.resolve()

    print(
        "Building frozen V2 repository runtime...",
    )

    runtime = build_runtime(
        repo,
        embedding="bge",
        # The engine's reranker is not used by
        # V5. V2 comes directly from hybrid.
        reranker="heuristic",
    )

    print(
        "Loading local Qwen provider...",
    )

    provider = (
        TransformersCoderProvider(
            model=args.model,
        )
    )

    agent = V5InvestigationAgent(
        repo=repo,
        runtime=runtime,
        provider=provider,
    )

    print(
        "Running V5 investigation...",
    )

    report = agent.investigate(
        args.task,
    )

    payload = json.dumps(
        report,
        indent=2,
    )

    print()
    print(payload)

    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            payload + "\n",
            encoding="utf-8",
        )

        print()
        print(
            "Saved:",
            args.output,
        )


if __name__ == "__main__":
    main()
