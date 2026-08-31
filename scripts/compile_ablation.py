from __future__ import annotations

import json
from pathlib import Path


def load(path: str, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def main() -> None:
    retrieval = load("reports/experiments/retrieval_fixture.json", [])
    graph = load("reports/experiments/graph_ablation_fixture.json", [])
    agent = load("reports/experiments/agent_fixture.json", {})
    patch = load("reports/experiments/safe_patch_fixture.json", {})
    rows = []
    for row in retrieval:
        rows.append(
            {
                "Architecture": row["version"],
                "File R@10": row["file_r10"],
                "Symbol R@10": row["symbol_r10"],
                "MRR": row["mrr"],
                "Test R@10": "fixture-only",
                "Task Success": "n/a",
                "Latency": "not-recorded-in-fixture-script",
            }
        )
    if graph:
        g2 = next((x for x in graph if x["graph_hops"] == 2), graph[-1])
        rows.append(
            {
                "Architecture": "V4",
                "File R@10": "fixture-only",
                "Symbol R@10": "fixture-only",
                "MRR": "fixture-only",
                "Test R@10": 1.0 if g2.get("related_tests") else 0.0,
                "Task Success": "n/a",
                "Latency": "not-recorded",
            }
        )
    rows.append(
        {
            "Architecture": "V5",
            "File R@10": "fixture-only",
            "Symbol R@10": "fixture-only",
            "MRR": "fixture-only",
            "Test R@10": "fixture-only",
            "Task Success": bool(agent.get("completed")),
            "Latency": "not-recorded",
        }
    )
    rows.append(
        {
            "Architecture": "V6",
            "File R@10": "fixture-only",
            "Symbol R@10": "fixture-only",
            "MRR": "fixture-only",
            "Test R@10": "fixture-only",
            "Task Success": bool(patch.get("verification", {}).get("passed")),
            "Latency": "not-recorded",
        }
    )
    out = Path("reports/experiments/ablation_fixture.json")
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
