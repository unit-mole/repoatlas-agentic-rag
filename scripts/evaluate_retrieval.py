from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import networkx as nx

from repoatlas.evaluation.retrieval_metrics import (
    mrr,
    ndcg_at_k,
    recall_at_k,
)
from repoatlas.pipeline import build_runtime
from repoatlas.schemas.evaluation import EvaluationCase
from repoatlas.schemas.retrieval import RetrievedCode

RELATIONSHIP_WEIGHT = {
    "TESTS": 1.00,
    "CALLS": 0.90,
    "REFERENCES": 0.65,
    "CONTAINS": 0.55,
}


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _symbol_key(item: RetrievedCode) -> str:
    return f"{item.file_path}::{item.qualified_symbol}"


def _rankings_from_hits(
    hits: list[RetrievedCode],
) -> tuple[list[str], list[str]]:
    files = _unique([item.file_path for item in hits])
    symbols = _unique([_symbol_key(item) for item in hits])
    return files, symbols


def _test_files(files: list[str]) -> list[str]:
    return [
        path
        for path in files
        if path.startswith(("tests/", "test/")) or Path(path).name.startswith("test_")
    ]


def _metrics(
    *,
    files: list[str],
    symbols: list[str],
    case: EvaluationCase,
    latency_ms: float,
) -> dict[str, Any]:
    tests = _test_files(files)

    return {
        "file_recall_at_5": recall_at_k(
            files,
            case.expected_changed_files,
            5,
        ),
        "file_recall_at_10": recall_at_k(
            files,
            case.expected_changed_files,
            10,
        ),
        "symbol_recall_at_5": recall_at_k(
            symbols,
            case.expected_changed_symbols,
            5,
        ),
        "symbol_recall_at_10": recall_at_k(
            symbols,
            case.expected_changed_symbols,
            10,
        ),
        "file_mrr": mrr(
            files,
            case.expected_changed_files,
        ),
        "file_ndcg_at_10": ndcg_at_k(
            files,
            case.expected_changed_files,
            10,
        ),
        "test_file_recall_at_10": recall_at_k(
            tests,
            case.expected_tests,
            10,
        ),
        "latency_ms": round(latency_ms, 3),
    }


def _timed(fn):
    start = time.perf_counter()
    value = fn()
    elapsed = (time.perf_counter() - start) * 1000
    return value, elapsed


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


def _graph_augmented_ranking(
    *,
    direct_hits: list[RetrievedCode],
    graph: nx.MultiDiGraph,
    max_hops: int,
    max_added_nodes: int = 25,
) -> tuple[
    list[str],
    list[str],
    list[dict[str, Any]],
]:
    scores: dict[str, float] = {}
    evidence: dict[str, dict[str, Any]] = {}

    direct_keys: set[str] = set()

    for rank, item in enumerate(
        direct_hits,
        start=1,
    ):
        key = _node_key(
            item.file_path,
            item.qualified_symbol,
        )

        if key not in graph:
            continue

        direct_keys.add(key)

        direct_score = 1.0 / rank + max(
            float(item.rerank_score),
            0.0,
        )

        scores[key] = max(
            scores.get(key, 0.0),
            direct_score,
        )

        evidence[key] = {
            "source": "direct",
            "rank": rank,
            "score": direct_score,
        }

    added: set[str] = set()

    for seed_rank, item in enumerate(
        direct_hits[:5],
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

                graph_score = (1.0 / seed_rank) * relation_weight * confidence / next_hop

                node_data = graph.nodes[neighbor]

                if node_data.get("type") == "symbol":
                    if graph_score > scores.get(
                        neighbor,
                        -math.inf,
                    ):
                        scores[neighbor] = graph_score

                        evidence[neighbor] = {
                            "source": seed,
                            "relationship": (relationship),
                            "hop": next_hop,
                            "confidence": (confidence),
                            "score": graph_score,
                        }

                    if neighbor not in direct_keys:
                        added.add(neighbor)

                frontier.append((neighbor, next_hop))

                if len(added) >= max_added_nodes:
                    frontier.clear()
                    break

            if len(added) >= max_added_nodes:
                break

        if len(added) >= max_added_nodes:
            break

    ranked_nodes = sorted(
        scores,
        key=lambda node: (
            -scores[node],
            node,
        ),
    )

    files: list[str] = []
    symbols: list[str] = []
    details: list[dict[str, Any]] = []

    for node in ranked_nodes:
        data = graph.nodes[node]

        if data.get("type") != "symbol":
            continue

        file_path = str(data.get("file_path", ""))
        qualified_symbol = str(data.get("symbol", ""))

        if not file_path or not qualified_symbol:
            continue

        files.append(file_path)
        symbols.append(f"{file_path}::{qualified_symbol}")

        details.append(
            {
                "file": file_path,
                "symbol": qualified_symbol,
                "score": round(
                    scores[node],
                    6,
                ),
                **evidence.get(node, {}),
            }
        )

    return (
        _unique(files),
        _unique(symbols),
        details,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo",
        required=True,
    )

    parser.add_argument(
        "--case",
        required=True,
    )

    parser.add_argument(
        "--embedding",
        choices=["hash", "bge"],
        default="bge",
    )

    parser.add_argument(
        "--reranker",
        choices=["heuristic", "bge"],
        default="bge",
    )

    parser.add_argument(
        "--graph-hops",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--output",
        default=None,
    )

    args = parser.parse_args()

    repo = Path(args.repo)

    case_path = Path(args.case)

    case = EvaluationCase.model_validate_json(case_path.read_text(encoding="utf-8"))

    build_start = time.perf_counter()

    runtime = build_runtime(
        repo,
        embedding=args.embedding,
        reranker=args.reranker,
    )

    runtime_build_seconds = time.perf_counter() - build_start

    query = case.issue_text

    rows: list[dict[str, Any]] = []

    v0_hits, latency = _timed(
        lambda: runtime["lexical"].search(
            query,
            40,
        )
    )

    files, symbols = _rankings_from_hits(v0_hits)

    rows.append(
        {
            "version": "V0",
            "method": "BM25 lexical",
            **_metrics(
                files=files,
                symbols=symbols,
                case=case,
                latency_ms=latency,
            ),
            "top_files": files[:10],
            "top_symbols": symbols[:10],
        }
    )

    v1_hits, latency = _timed(
        lambda: runtime["dense"].search(
            query,
            40,
        )
    )

    files, symbols = _rankings_from_hits(v1_hits)

    rows.append(
        {
            "version": "V1",
            "method": ("BGE-M3 dense"),
            **_metrics(
                files=files,
                symbols=symbols,
                case=case,
                latency_ms=latency,
            ),
            "top_files": files[:10],
            "top_symbols": symbols[:10],
        }
    )

    v2_hits, latency = _timed(
        lambda: runtime["hybrid"].search(
            query,
            lexical_k=40,
            dense_k=40,
            fusion_k=30,
        )
    )

    files, symbols = _rankings_from_hits(v2_hits)

    rows.append(
        {
            "version": "V2",
            "method": ("BM25 + BGE-M3 RRF"),
            **_metrics(
                files=files,
                symbols=symbols,
                case=case,
                latency_ms=latency,
            ),
            "top_files": files[:10],
            "top_symbols": symbols[:10],
        }
    )

    v3_hits, latency = _timed(
        lambda: runtime["reranker"].rerank(
            query,
            v2_hits,
            12,
        )
    )

    files, symbols = _rankings_from_hits(v3_hits)

    rows.append(
        {
            "version": "V3",
            "method": ("Hybrid + BGE reranker"),
            **_metrics(
                files=files,
                symbols=symbols,
                case=case,
                latency_ms=latency,
            ),
            "top_files": files[:10],
            "top_symbols": symbols[:10],
        }
    )

    (
        graph_result,
        latency,
    ) = _timed(
        lambda: _graph_augmented_ranking(
            direct_hits=v3_hits,
            graph=runtime["graph"],
            max_hops=args.graph_hops,
        )
    )

    (
        files,
        symbols,
        graph_details,
    ) = graph_result

    rows.append(
        {
            "version": "V4",
            "method": (f"Hybrid + reranker + graph {args.graph_hops}-hop"),
            **_metrics(
                files=files,
                symbols=symbols,
                case=case,
                latency_ms=latency,
            ),
            "top_files": files[:10],
            "top_symbols": symbols[:10],
            "graph_candidates": (graph_details[:25]),
        }
    )

    result = {
        "case_id": case.case_id,
        "repository": case.repository,
        "base_commit": case.base_commit,
        "fix_commit": case.fix_commit,
        "embedding": args.embedding,
        "reranker": args.reranker,
        "graph_hops": args.graph_hops,
        "runtime_build_seconds": round(
            runtime_build_seconds,
            3,
        ),
        "gold": {
            "changed_files": len(case.expected_changed_files),
            "changed_symbols": len(case.expected_changed_symbols),
            "tests": len(case.expected_tests),
        },
        "results": rows,
    }

    if args.output:
        output = Path(args.output)
    else:
        output = Path("reports/experiments") / (f"retrieval_{case.case_id}.json")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
