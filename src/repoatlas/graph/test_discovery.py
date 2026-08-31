from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from repoatlas.schemas.retrieval import RetrievedCode


@dataclass(frozen=True)
class TestCandidate:
    file_path: str
    best_source_rank: int
    supporting_edges: int
    supporting_sources: int
    evidence: list[dict[str, Any]] = field(default_factory=list)


def _is_test_file(path: str) -> bool:
    return path.startswith(("tests/", "test/")) or Path(path).name.startswith("test_")


def discover_related_tests(
    graph: nx.MultiDiGraph,
    source_hits: list[RetrievedCode],
    *,
    limit: int = 20,
) -> list[TestCandidate]:
    """Discover tests through reverse TESTS edges.

    This is intentionally an untuned baseline.

    Ranking priority:
    1. Best source-symbol retrieval rank.
    2. Number of distinct supporting source symbols.
    3. Number of TESTS edges.
    4. Stable path ordering.

    The function does not use benchmark gold labels.
    """

    records: dict[str, dict[str, Any]] = {}

    for source_rank, hit in enumerate(
        source_hits,
        start=1,
    ):
        source_node = f"sym:{hit.file_path}:{hit.qualified_symbol}"

        if source_node not in graph:
            continue

        for test_node, _, edge in graph.in_edges(
            source_node,
            data=True,
        ):
            if edge.get("relationship") != "TESTS":
                continue

            node_data = graph.nodes[test_node]

            if node_data.get("type") != "symbol":
                continue

            test_file = str(node_data.get("file_path", ""))

            if not test_file or not _is_test_file(test_file):
                continue

            if test_file not in records:
                records[test_file] = {
                    "best_source_rank": source_rank,
                    "sources": set(),
                    "edges": 0,
                    "evidence": [],
                }

            record = records[test_file]

            record["best_source_rank"] = min(
                record["best_source_rank"],
                source_rank,
            )

            source_key = f"{hit.file_path}::{hit.qualified_symbol}"

            record["sources"].add(source_key)
            record["edges"] += 1

            record["evidence"].append(
                {
                    "source_rank": source_rank,
                    "source_file": hit.file_path,
                    "source_symbol": (hit.qualified_symbol),
                    "test_symbol": str(node_data.get("symbol", "")),
                    "confidence": float(edge.get("confidence", 1.0)),
                }
            )

    ranked = sorted(
        records.items(),
        key=lambda item: (
            item[1]["best_source_rank"],
            -len(item[1]["sources"]),
            -item[1]["edges"],
            item[0],
        ),
    )

    return [
        TestCandidate(
            file_path=path,
            best_source_rank=data["best_source_rank"],
            supporting_edges=data["edges"],
            supporting_sources=len(data["sources"]),
            evidence=data["evidence"],
        )
        for path, data in ranked[:limit]
    ]
