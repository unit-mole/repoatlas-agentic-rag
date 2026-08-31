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
from repoatlas.graph.protected_augmentation import (
    protected_graph_augmentation,
)
from repoatlas.pipeline import build_runtime
from repoatlas.schemas.evaluation import (
    EvaluationCase,
)
from repoatlas.schemas.retrieval import (
    RetrievedCode,
)


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _rankings(
    hits: list[RetrievedCode],
) -> tuple[list[str], list[str]]:
    files = _unique([item.file_path for item in hits])

    symbols = _unique([(f"{item.file_path}::{item.qualified_symbol}") for item in hits])

    return files, symbols


def _test_files(
    files: list[str],
) -> list[str]:
    return [
        path
        for path in files
        if (path.startswith(("tests/", "test/")) or Path(path).name.startswith("test_"))
    ]


def _metrics(
    *,
    files: list[str],
    symbols: list[str],
    case: EvaluationCase,
) -> dict[str, float]:
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
        "file_recall_at_20": recall_at_k(
            files,
            case.expected_changed_files,
            20,
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
        "symbol_recall_at_20": recall_at_k(
            symbols,
            case.expected_changed_symbols,
            20,
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
        "test_file_recall_at_10": (
            recall_at_k(
                tests,
                case.expected_tests,
                10,
            )
        ),
    }


def _timed(fn):
    start = time.perf_counter()
    value = fn()
    elapsed = (time.perf_counter() - start) * 1000

    return value, elapsed


def main() -> None:
    case_paths = sorted(Path("benchmark/cases").glob("httpx-dev-*.json"))

    if len(case_paths) != 5:
        raise RuntimeError("Expected exactly 5 DEV cases.")

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

        runtime = build_runtime(
            repo,
            embedding="bge",
            reranker="heuristic",
        )

        v2_hits, v2_latency = _timed(
            lambda runtime=runtime, case=case: runtime["hybrid"].search(
                case.issue_text,
                lexical_k=40,
                dense_k=40,
                fusion_k=30,
            )
        )

        (
            v2_files,
            v2_symbols,
        ) = _rankings(v2_hits)

        protected, graph_latency = _timed(
            lambda v2_hits=v2_hits, runtime=runtime: protected_graph_augmentation(
                direct_hits=v2_hits,
                graph=runtime["graph"],
                max_hops=1,
                seed_limit=5,
                max_added_nodes=25,
                protected_symbol_k=10,
                protected_file_k=10,
            )
        )

        # This is the defining V4P invariant.
        #
        # Preserve every available direct V2 result up to the
        # evaluation cutoff. If V2 contains fewer than 10 unique
        # files, graph augmentation may fill the remaining slots.
        file_k = min(
            10,
            len(v2_files),
        )

        symbol_k = min(
            10,
            len(v2_symbols),
        )

        if protected.files[:file_k] != v2_files[:file_k]:
            raise RuntimeError(f"{case.case_id}: V4P changed protected direct file ranking.")

        if protected.symbols[:symbol_k] != v2_symbols[:symbol_k]:
            raise RuntimeError(f"{case.case_id}: V4P changed protected direct symbol ranking.")

        v2_metrics = _metrics(
            files=v2_files,
            symbols=v2_symbols,
            case=case,
        )

        v4p_metrics = _metrics(
            files=protected.files,
            symbols=protected.symbols,
            case=case,
        )

        graph_files = _unique([item["file"] for item in protected.graph_candidates])

        graph_symbols = [
            (f"{item['file']}::{item['symbol']}") for item in protected.graph_candidates
        ]

        gold_graph_files = sorted(set(graph_files) & set(case.expected_changed_files))

        gold_graph_symbols = sorted(set(graph_symbols) & set(case.expected_changed_symbols))

        result = {
            "case_id": case.case_id,
            "V2": {
                "metrics": v2_metrics,
                "latency_ms": round(
                    v2_latency,
                    3,
                ),
            },
            "V4P": {
                "metrics": v4p_metrics,
                "graph_stage_latency_ms": (
                    round(
                        graph_latency,
                        3,
                    )
                ),
                "end_to_end_latency_ms": (
                    round(
                        v2_latency + graph_latency,
                        3,
                    )
                ),
                "protected_prefix_size": (protected.protected_prefix_size),
                "graph_candidates": len(protected.graph_candidates),
                "graph_added_files": len(graph_files),
                "gold_graph_files": (gold_graph_files),
                "gold_graph_symbols": (gold_graph_symbols),
            },
        }

        results.append(result)

        print(
            "V2  FileR@10={:.3f} FileR@20={:.3f} SymR@10={:.3f} SymR@20={:.3f}".format(
                v2_metrics["file_recall_at_10"],
                v2_metrics["file_recall_at_20"],
                v2_metrics["symbol_recall_at_10"],
                v2_metrics["symbol_recall_at_20"],
            )
        )

        print(
            "V4P FileR@10={:.3f} FileR@20={:.3f} SymR@10={:.3f} SymR@20={:.3f}".format(
                v4p_metrics["file_recall_at_10"],
                v4p_metrics["file_recall_at_20"],
                v4p_metrics["symbol_recall_at_10"],
                v4p_metrics["symbol_recall_at_20"],
            )
        )

        print(
            "Protected prefix:",
            protected.protected_prefix_size,
        )

        print(
            "Graph candidates:",
            len(protected.graph_candidates),
        )

        print(
            "Gold graph files:",
            gold_graph_files,
        )

        print(
            "Gold graph symbols:",
            gold_graph_symbols,
        )

    metric_names = [
        "file_recall_at_5",
        "file_recall_at_10",
        "file_recall_at_20",
        "symbol_recall_at_5",
        "symbol_recall_at_10",
        "symbol_recall_at_20",
        "file_mrr",
        "file_ndcg_at_10",
        "test_file_recall_at_10",
    ]

    macro = {
        version: {
            metric: mean(row[version]["metrics"][metric] for row in results)
            for metric in metric_names
        }
        for version in (
            "V2",
            "V4P",
        )
    }

    output = {
        "case_count": len(results),
        "design": ("V2 protected top-10 + bounded deterministic 1-hop graph augmentation"),
        "results": results,
        "macro": macro,
    }

    output_path = Path("reports/experiments/httpx-dev-v4p-protected-graph.json")

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
    print("HTTPX DEV V2 vs V4P")
    print("=" * 76)
    print()

    header = (
        f"{'Ver':<5}"
        f"{'FileR5':>9}"
        f"{'FileR10':>10}"
        f"{'FileR20':>10}"
        f"{'SymR5':>9}"
        f"{'SymR10':>10}"
        f"{'SymR20':>10}"
        f"{'MRR':>9}"
        f"{'nDCG10':>10}"
    )

    print(header)
    print("-" * len(header))

    for version in (
        "V2",
        "V4P",
    ):
        row = macro[version]

        print(
            f"{version:<5}"
            f"{row['file_recall_at_5']:>9.3f}"
            f"{row['file_recall_at_10']:>10.3f}"
            f"{row['file_recall_at_20']:>10.3f}"
            f"{row['symbol_recall_at_5']:>9.3f}"
            f"{row['symbol_recall_at_10']:>10.3f}"
            f"{row['symbol_recall_at_20']:>10.3f}"
            f"{row['file_mrr']:>9.3f}"
            f"{row['file_ndcg_at_10']:>10.3f}"
        )

    print()
    print("V4P PROTECTED GRAPH DEV EXPERIMENT: PASS")

    print(
        "Saved:",
        output_path,
    )


if __name__ == "__main__":
    main()
