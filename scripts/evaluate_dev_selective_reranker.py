from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

from repoatlas.evaluation.retrieval_metrics import (
    mrr,
    ndcg_at_k,
    recall_at_k,
)
from repoatlas.pipeline import build_runtime
from repoatlas.reranking.reranker import BGEReranker
from repoatlas.reranking.selective import (
    merge_symbol_ranking,
    select_symbol_candidates,
    symbol_key,
)
from repoatlas.schemas.evaluation import EvaluationCase


def _unique(
    items: list[str],
) -> list[str]:
    return list(dict.fromkeys(items))


def _timed(fn):
    start = time.perf_counter()
    result = fn()
    latency = (time.perf_counter() - start) * 1000

    return result, latency


def _symbol_metrics(
    symbols: list[str],
    case: EvaluationCase,
) -> dict[str, float]:
    return {
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
        "symbol_recall_at_20": recall_at_k(
            symbols,
            case.expected_changed_symbols,
            20,
        ),
    }


def _file_metrics(
    files: list[str],
    case: EvaluationCase,
) -> dict[str, float]:
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
        "file_mrr": mrr(
            files,
            case.expected_changed_files,
        ),
        "file_ndcg_at_10": ndcg_at_k(
            files,
            case.expected_changed_files,
            10,
        ),
    }


def main() -> None:
    case_paths = sorted(Path("benchmark/cases").glob("httpx-dev-*.json"))

    if len(case_paths) != 5:
        raise RuntimeError("Expected exactly five DEV cases.")

    # Load the cross-encoder ONCE for the entire benchmark.
    print("Loading BGE cross-encoder once...")
    reranker = BGEReranker()

    results: list[dict[str, Any]] = []

    for index, case_path in enumerate(
        case_paths,
        start=1,
    ):
        case = EvaluationCase.model_validate_json(case_path.read_text(encoding="utf-8"))

        repo = Path("data/snapshots") / case.case_id

        print()
        print("=" * 76)
        print(f"[{index}/5] {case.case_id}")
        print("=" * 76)

        # We need BGE embeddings, but NOT another BGE
        # cross-encoder instance inside build_runtime.
        runtime = build_runtime(
            repo,
            embedding="bge",
            reranker="heuristic",
        )

        v2_hits, retrieval_ms = _timed(
            lambda runtime=runtime, case=case: runtime["hybrid"].search(
                case.issue_text,
                lexical_k=40,
                dense_k=40,
                fusion_k=30,
            )
        )

        v2_files = _unique([item.file_path for item in v2_hits])

        v2_symbols = _unique([symbol_key(item) for item in v2_hits])

        candidates = select_symbol_candidates(
            v2_hits,
            file_limit=5,
            candidate_limit=12,
        )

        reranked, rerank_ms = _timed(
            lambda reranker=reranker, case=case, candidates=candidates: reranker.rerank(
                case.issue_text,
                candidates,
                top_k=len(candidates),
            )
        )

        v3s_symbols = merge_symbol_ranking(
            reranked,
            v2_hits,
        )

        # V3S must never own or change file ranking.
        v3s_files = list(v2_files)

        if v3s_files != v2_files:
            raise RuntimeError(f"{case.case_id}: V3S modified V2 file ranking.")

        v2_symbol_metrics = _symbol_metrics(
            v2_symbols,
            case,
        )

        v3s_symbol_metrics = _symbol_metrics(
            v3s_symbols,
            case,
        )

        file_metrics = _file_metrics(
            v2_files,
            case,
        )

        result = {
            "case_id": case.case_id,
            "candidate_files": _unique([item.file_path for item in candidates]),
            "candidate_count": len(candidates),
            "V2": {
                "file_metrics": file_metrics,
                "symbol_metrics": (v2_symbol_metrics),
                "retrieval_latency_ms": round(
                    retrieval_ms,
                    3,
                ),
            },
            "V3S": {
                "file_metrics": file_metrics,
                "symbol_metrics": (v3s_symbol_metrics),
                "reranker_stage_latency_ms": (
                    round(
                        rerank_ms,
                        3,
                    )
                ),
                "end_to_end_latency_ms": (
                    round(
                        retrieval_ms + rerank_ms,
                        3,
                    )
                ),
                "top_symbols": (v3s_symbols[:10]),
            },
        }

        results.append(result)

        print(
            "Candidates scored:",
            len(candidates),
        )

        print(
            "V2  SymR@5={:.3f} SymR@10={:.3f} SymR@20={:.3f}".format(
                v2_symbol_metrics["symbol_recall_at_5"],
                v2_symbol_metrics["symbol_recall_at_10"],
                v2_symbol_metrics["symbol_recall_at_20"],
            )
        )

        print(
            "V3S SymR@5={:.3f} SymR@10={:.3f} SymR@20={:.3f}".format(
                v3s_symbol_metrics["symbol_recall_at_5"],
                v3s_symbol_metrics["symbol_recall_at_10"],
                v3s_symbol_metrics["symbol_recall_at_20"],
            )
        )

        print(
            "Selective reranker:",
            round(rerank_ms, 1),
            "ms",
        )

    symbol_metrics = [
        "symbol_recall_at_5",
        "symbol_recall_at_10",
        "symbol_recall_at_20",
    ]

    macro = {
        version: {
            metric: mean(row[version]["symbol_metrics"][metric] for row in results)
            for metric in symbol_metrics
        }
        for version in ("V2", "V3S")
    }

    macro["V2"]["file_recall_at_10"] = mean(
        row["V2"]["file_metrics"]["file_recall_at_10"] for row in results
    )

    macro["V3S"]["file_recall_at_10"] = macro["V2"]["file_recall_at_10"]

    macro["V2"]["retrieval_latency_ms"] = mean(row["V2"]["retrieval_latency_ms"] for row in results)

    macro["V3S"]["reranker_stage_latency_ms"] = mean(
        row["V3S"]["reranker_stage_latency_ms"] for row in results
    )

    macro["V3S"]["end_to_end_latency_ms"] = mean(
        row["V3S"]["end_to_end_latency_ms"] for row in results
    )

    output = {
        "case_count": len(results),
        "design": {
            "base": "V2 Hybrid",
            "file_ranking": "V2 locked",
            "file_limit": 5,
            "candidate_limit": 12,
            "reranker": ("BAAI/bge-reranker-v2-m3"),
        },
        "results": results,
        "macro": macro,
    }

    output_path = Path("reports/experiments/httpx-dev-v3s-selective-reranker.json")

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 76)
    print("HTTPX DEV V2 vs V3S SELECTIVE RERANKER")
    print("=" * 76)
    print()

    print(f"{'Ver':<5}{'FileR10':>10}{'SymR5':>10}{'SymR10':>10}{'SymR20':>10}")

    print("-" * 45)

    for version in ("V2", "V3S"):
        row = macro[version]

        print(
            f"{version:<5}"
            f"{row['file_recall_at_10']:>10.3f}"
            f"{row['symbol_recall_at_5']:>10.3f}"
            f"{row['symbol_recall_at_10']:>10.3f}"
            f"{row['symbol_recall_at_20']:>10.3f}"
        )

    print()

    print(
        "Mean V2 retrieval:",
        round(
            macro["V2"]["retrieval_latency_ms"],
            1,
        ),
        "ms",
    )

    print(
        "Mean V3S reranker stage:",
        round(
            macro["V3S"]["reranker_stage_latency_ms"],
            1,
        ),
        "ms",
    )

    print(
        "Mean V3S end-to-end:",
        round(
            macro["V3S"]["end_to_end_latency_ms"],
            1,
        ),
        "ms",
    )

    print()
    print("V3S SELECTIVE RERANKER DEV EXPERIMENT: PASS")

    print(
        "Saved:",
        output_path,
    )


if __name__ == "__main__":
    main()
