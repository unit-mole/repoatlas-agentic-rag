import argparse
import json
from pathlib import Path

from repoatlas.pipeline import build_runtime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="data/fixture_repo")
    ap.add_argument(
        "--task",
        default="Changing cache timeout behavior may affect token refresh and related tests",
    )
    a = ap.parse_args()
    rt = build_runtime(Path(a.repo))
    rows = []
    for hops in [0, 1, 2]:
        r = rt["engine"].investigate(a.task, hops)
        rows.append(
            {
                "graph_hops": hops,
                "affected_files": [x["file"] for x in r["likely_affected_files"]],
                "related_tests": r["related_tests"],
                "graph_edges_added": len(r["dependency_evidence"]),
            }
        )
    p = Path("reports/experiments/graph_ablation_fixture.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
