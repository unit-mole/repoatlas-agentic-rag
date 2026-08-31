from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from repoatlas.evaluation.retrieval_metrics import (
    mrr,
    recall_at_k,
)
from repoatlas.graph.test_discovery import (
    discover_related_tests,
)
from repoatlas.pipeline import build_runtime
from repoatlas.schemas.evaluation import EvaluationCase


def _gold_ranks(
    predicted: list[str],
    gold: list[str],
) -> dict[str, int | None]:
    result = {}

    for target in gold:
        rank = next(
            (
                index
                for index, path in enumerate(
                    predicted,
                    start=1,
                )
                if path == target
            ),
            None,
        )

        result[target] = rank

    return result


def _metrics(
    predicted: list[str],
    gold: list[str],
) -> dict[str, float]:
    return {
        "changed_test_recall_at_10": recall_at_k(
            predicted,
            gold,
            10,
        ),
        "changed_test_recall_at_20": recall_at_k(
            predicted,
            gold,
            20,
        ),
        "changed_test_mrr": mrr(
            predicted,
            gold,
        ),
    }


def main() -> None:
    case_paths = sorted(Path("benchmark/cases").glob("httpx-dev-*.json"))

    if len(case_paths) != 5:
        raise RuntimeError(f"Expected 5 DEV cases, found {len(case_paths)}")

    results = []

    for index, case_path in enumerate(
        case_paths,
        start=1,
    ):
        case = EvaluationCase.model_validate_json(case_path.read_text(encoding="utf-8"))

        repo = Path("data/snapshots") / case.case_id

        print()
        print("=" * 76)
        print(f"[{index}/{len(case_paths)}] {case.case_id}")
        print("=" * 76)

        print("Building runtime...")

        runtime = build_runtime(
            repo,
            embedding="bge",
            reranker="bge",
        )

        hybrid = runtime["hybrid"].search(
            case.issue_text,
            lexical_k=40,
            dense_k=40,
            fusion_k=30,
        )

        reranked = runtime["reranker"].rerank(
            case.issue_text,
            hybrid,
            12,
        )

        v2_candidates = discover_related_tests(
            runtime["graph"],
            hybrid,
            limit=30,
        )

        v3_candidates = discover_related_tests(
            runtime["graph"],
            reranked,
            limit=30,
        )

        v2_predicted = [item.file_path for item in v2_candidates]

        v3_predicted = [item.file_path for item in v3_candidates]

        gold = list(case.expected_tests)

        v2_metrics = _metrics(
            v2_predicted,
            gold,
        )

        v3_metrics = _metrics(
            v3_predicted,
            gold,
        )

        result = {
            "case_id": case.case_id,
            "gold_changed_tests": gold,
            "V2_graph_test_discovery": {
                "metrics": v2_metrics,
                "gold_ranks": _gold_ranks(
                    v2_predicted,
                    gold,
                ),
                "predicted_tests": (v2_predicted),
            },
            "V3_graph_test_discovery": {
                "metrics": v3_metrics,
                "gold_ranks": _gold_ranks(
                    v3_predicted,
                    gold,
                ),
                "predicted_tests": (v3_predicted),
            },
        }

        results.append(result)

        print("Gold:", gold)

        print(
            "V2  R@10={:.3f} R@20={:.3f} MRR={:.3f}".format(
                v2_metrics["changed_test_recall_at_10"],
                v2_metrics["changed_test_recall_at_20"],
                v2_metrics["changed_test_mrr"],
            )
        )

        print(
            "V3  R@10={:.3f} R@20={:.3f} MRR={:.3f}".format(
                v3_metrics["changed_test_recall_at_10"],
                v3_metrics["changed_test_recall_at_20"],
                v3_metrics["changed_test_mrr"],
            )
        )

        print(
            "V2 gold ranks:",
            result["V2_graph_test_discovery"]["gold_ranks"],
        )

        print(
            "V3 gold ranks:",
            result["V3_graph_test_discovery"]["gold_ranks"],
        )

    versions = {
        "V2_graph_test_discovery": [],
        "V3_graph_test_discovery": [],
    }

    for result in results:
        for version, rows in versions.items():
            rows.append(result[version]["metrics"])

    macro = {}

    for version, rows in versions.items():
        macro[version] = {
            "changed_test_recall_at_10": mean(row["changed_test_recall_at_10"] for row in rows),
            "changed_test_recall_at_20": mean(row["changed_test_recall_at_20"] for row in rows),
            "changed_test_mrr": mean(row["changed_test_mrr"] for row in rows),
        }

    output = {
        "case_count": len(results),
        "results": results,
        "macro": macro,
    }

    output_path = Path("reports/experiments/httpx-dev-test-discovery.json")

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
    print("HTTPX DEV CHANGED-TEST DISCOVERY")
    print("=" * 76)

    print()
    print(f"{'Source':<12}{'R@10':>10}{'R@20':>10}{'MRR':>10}")

    print("-" * 42)

    for label, key in (
        (
            "V2 Hybrid",
            "V2_graph_test_discovery",
        ),
        (
            "V3 Rerank",
            "V3_graph_test_discovery",
        ),
    ):
        row = macro[key]

        print(
            f"{label:<12}"
            f"{row['changed_test_recall_at_10']:>10.3f}"
            f"{row['changed_test_recall_at_20']:>10.3f}"
            f"{row['changed_test_mrr']:>10.3f}"
        )

    print()
    print("MULTI-CASE TEST DISCOVERY: PASS")
    print(
        "Saved:",
        output_path,
    )


if __name__ == "__main__":
    main()
