from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

METRICS = [
    "file_recall_at_5",
    "file_recall_at_10",
    "symbol_recall_at_5",
    "symbol_recall_at_10",
    "file_mrr",
    "file_ndcg_at_10",
    "test_file_recall_at_10",
    "latency_ms",
]


def main() -> None:
    root = Path("reports/experiments/dev")

    paths = sorted(root.glob("httpx-dev-*-v0-v4.json"))

    if len(paths) != 5:
        raise RuntimeError(f"Expected 5 DEV result files, found {len(paths)}.")

    per_case = []
    grouped = defaultdict(lambda: defaultdict(list))

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))

        case_id = data["case_id"]

        for row in data["results"]:
            version = row["version"]

            record = {
                "case_id": case_id,
                "version": version,
            }

            for metric in METRICS:
                value = row[metric]

                record[metric] = value

                grouped[version][metric].append(float(value))

            per_case.append(record)

    versions = [
        "V0",
        "V1",
        "V2",
        "V3",
        "V4",
    ]

    macro = {}

    for version in versions:
        macro[version] = {metric: mean(grouped[version][metric]) for metric in METRICS}

    output = {
        "case_count": len(paths),
        "aggregation": ("macro mean across historical DEV cases"),
        "per_case": per_case,
        "macro": macro,
    }

    output_path = Path("reports/experiments/httpx-dev-v0-v4-aggregate.json")

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=== HTTPX DEV V0-V4 MACRO RESULTS ===")
    print()

    header = (
        f"{'Ver':<4}"
        f"{'FileR@5':>10}"
        f"{'FileR@10':>11}"
        f"{'SymR@5':>10}"
        f"{'SymR@10':>11}"
        f"{'MRR':>9}"
        f"{'nDCG@10':>11}"
        f"{'DirectTest':>12}"
        f"{'Latency':>11}"
    )

    print(header)
    print("-" * len(header))

    for version in versions:
        row = macro[version]

        print(
            f"{version:<4}"
            f"{row['file_recall_at_5']:>10.3f}"
            f"{row['file_recall_at_10']:>11.3f}"
            f"{row['symbol_recall_at_5']:>10.3f}"
            f"{row['symbol_recall_at_10']:>11.3f}"
            f"{row['file_mrr']:>9.3f}"
            f"{row['file_ndcg_at_10']:>11.3f}"
            f"{row['test_file_recall_at_10']:>12.3f}"
            f"{row['latency_ms']:>11.1f}"
        )

    print()
    print(
        "Cases:",
        len(paths),
    )
    print("Aggregation: MACRO mean")
    print(
        "Saved:",
        output_path,
    )
    print()
    print("MULTI-CASE DEV AGGREGATION: PASS")


if __name__ == "__main__":
    main()
