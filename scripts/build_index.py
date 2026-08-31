import argparse
import json
from pathlib import Path

from repoatlas.pipeline import build_runtime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--embedding", choices=["hash", "bge"], default="hash")
    a = ap.parse_args()
    rt = build_runtime(Path(a.repo), embedding=a.embedding)
    out = Path("data/processed") / Path(a.repo).name
    out.mkdir(parents=True, exist_ok=True)
    (out / "index_manifest.json").write_text(
        json.dumps(
            {"embedding": a.embedding, "chunks": len(rt["chunks"]), "status": "built"}, indent=2
        )
    )
    print((out / "index_manifest.json").read_text())


if __name__ == "__main__":
    main()
