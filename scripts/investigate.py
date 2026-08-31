import argparse
import json
from pathlib import Path

from repoatlas.pipeline import build_runtime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--embedding", default="hash")
    ap.add_argument("--reranker", default="heuristic")
    ap.add_argument("--graph-hops", type=int, default=2)
    a = ap.parse_args()
    rt = build_runtime(Path(a.repo), a.embedding, a.reranker)
    print(json.dumps(rt["engine"].investigate(a.task, a.graph_hops), indent=2))


if __name__ == "__main__":
    main()
