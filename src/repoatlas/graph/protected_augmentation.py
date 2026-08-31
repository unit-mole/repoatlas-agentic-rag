from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from repoatlas.schemas.retrieval import RetrievedCode

RELATIONSHIP_WEIGHT = {
    "TESTS": 1.00,
    "CALLS": 0.90,
    "REFERENCES": 0.65,
    "CONTAINS": 0.55,
}


@dataclass(frozen=True)
class ProtectedGraphRanking:
    files: list[str]
    symbols: list[str]
    graph_candidates: list[dict[str, Any]]
    protected_prefix_size: int


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _symbol_key(item: RetrievedCode) -> str:
    return f"{item.file_path}::{item.qualified_symbol}"


def _node_key(
    file_path: str,
    qualified_symbol: str,
) -> str:
    return f"sym:{file_path}:{qualified_symbol}"


def _neighbors(
    graph: nx.MultiDiGraph,
    node: str,
) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []

    for _, target, data in graph.out_edges(
        node,
        data=True,
    ):
        found.append((target, dict(data)))

    for source, _, data in graph.in_edges(
        node,
        data=True,
    ):
        found.append((source, dict(data)))

    return sorted(
        found,
        key=lambda item: (
            item[0],
            str(
                item[1].get(
                    "relationship",
                    "",
                )
            ),
        ),
    )


def _protected_prefix_size(
    hits: list[RetrievedCode],
    *,
    protected_symbol_k: int,
    protected_file_k: int,
) -> int:
    """Find the smallest direct prefix protecting both cutoffs."""

    files: set[str] = set()

    for index, item in enumerate(
        hits,
        start=1,
    ):
        files.add(item.file_path)

        if index >= protected_symbol_k and len(files) >= protected_file_k:
            return index

    return len(hits)


def protected_graph_augmentation(
    *,
    direct_hits: list[RetrievedCode],
    graph: nx.MultiDiGraph,
    max_hops: int = 1,
    seed_limit: int = 5,
    max_added_nodes: int = 25,
    protected_symbol_k: int = 10,
    protected_file_k: int = 10,
) -> ProtectedGraphRanking:
    """Add bounded graph evidence without disturbing direct top-K.

    Direct retrieval remains authoritative for the protected prefix.
    Graph-only symbols are inserted after that prefix and before the
    remaining direct candidates.

    This means graph expansion can increase deeper coverage while the
    primary top-10 retrieval decision remains stable.
    """

    if not direct_hits:
        return ProtectedGraphRanking(
            files=[],
            symbols=[],
            graph_candidates=[],
            protected_prefix_size=0,
        )

    prefix_size = _protected_prefix_size(
        direct_hits,
        protected_symbol_k=protected_symbol_k,
        protected_file_k=protected_file_k,
    )

    protected_hits = direct_hits[:prefix_size]

    remaining_hits = direct_hits[prefix_size:]

    all_direct_nodes = {
        _node_key(
            item.file_path,
            item.qualified_symbol,
        )
        for item in direct_hits
    }

    scores: dict[str, float] = {}
    evidence: dict[
        str,
        dict[str, Any],
    ] = {}

    added: set[str] = set()

    for seed_rank, item in enumerate(
        direct_hits[:seed_limit],
        start=1,
    ):
        seed = _node_key(
            item.file_path,
            item.qualified_symbol,
        )

        if seed not in graph:
            continue

        frontier = [(seed, 0)]
        visited = {seed}

        while frontier:
            current, hop = frontier.pop(0)

            if hop >= max_hops:
                continue

            for neighbor, edge in _neighbors(
                graph,
                current,
            ):
                if neighbor in visited:
                    continue

                visited.add(neighbor)

                next_hop = hop + 1

                relationship = str(
                    edge.get(
                        "relationship",
                        "",
                    )
                )

                confidence = float(
                    edge.get(
                        "confidence",
                        1.0,
                    )
                )

                relation_weight = RELATIONSHIP_WEIGHT.get(
                    relationship,
                    0.50,
                )

                score = (1.0 / seed_rank) * relation_weight * confidence / next_hop

                node_data = graph.nodes[neighbor]

                if node_data.get("type") == "symbol" and neighbor not in all_direct_nodes:
                    if score > scores.get(
                        neighbor,
                        float("-inf"),
                    ):
                        scores[neighbor] = score

                        evidence[neighbor] = {
                            "source": seed,
                            "relationship": (relationship),
                            "hop": next_hop,
                            "confidence": (confidence),
                            "score": score,
                        }

                    added.add(neighbor)

                frontier.append((neighbor, next_hop))

                if len(added) >= max_added_nodes:
                    frontier.clear()
                    break

            if len(added) >= max_added_nodes:
                break

        if len(added) >= max_added_nodes:
            break

    graph_nodes = sorted(
        scores,
        key=lambda node: (
            -scores[node],
            node,
        ),
    )

    protected_files = [item.file_path for item in protected_hits]

    protected_symbols = [_symbol_key(item) for item in protected_hits]

    graph_files: list[str] = []
    graph_symbols: list[str] = []
    graph_details: list[dict[str, Any]] = []

    for node in graph_nodes:
        data = graph.nodes[node]

        if data.get("type") != "symbol":
            continue

        file_path = str(
            data.get(
                "file_path",
                "",
            )
        )

        symbol = str(
            data.get(
                "symbol",
                "",
            )
        )

        if not file_path or not symbol:
            continue

        graph_files.append(file_path)

        graph_symbols.append(f"{file_path}::{symbol}")

        graph_details.append(
            {
                "file": file_path,
                "symbol": symbol,
                "score": round(
                    scores[node],
                    6,
                ),
                **evidence[node],
            }
        )

    remaining_files = [item.file_path for item in remaining_hits]

    remaining_symbols = [_symbol_key(item) for item in remaining_hits]

    files = _unique(protected_files + graph_files + remaining_files)

    symbols = _unique(protected_symbols + graph_symbols + remaining_symbols)

    return ProtectedGraphRanking(
        files=files,
        symbols=symbols,
        graph_candidates=graph_details,
        protected_prefix_size=prefix_size,
    )
