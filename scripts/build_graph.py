import argparse
import json
from pathlib import Path

import networkx as nx

from repoatlas.pipeline import build_runtime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    rt = build_runtime(Path(a.repo))
    g = rt["graph"]
    out = Path("data/processed") / Path(a.repo).name
    out.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, out / "graph.graphml")
    (out / "graph_summary.json").write_text(
        json.dumps({"nodes": g.number_of_nodes(), "edges": g.number_of_edges()}, indent=2)
    )
    print((out / "graph_summary.json").read_text())


if __name__ == "__main__":
    main()
