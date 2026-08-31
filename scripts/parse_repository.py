import argparse
import json
from pathlib import Path

from repoatlas.parsing.chunks import symbols_to_chunks
from repoatlas.parsing.symbols import extract_repository_symbols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    root = Path(a.repo)
    syms = extract_repository_symbols(root.name, root)
    chunks = symbols_to_chunks(syms)
    out = Path("data/processed") / root.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "symbols.json").write_text(
        json.dumps([x.model_dump(mode="json") for x in syms], indent=2)
    )
    (out / "chunks.json").write_text(
        json.dumps([x.model_dump(mode="json") for x in chunks], indent=2)
    )
    print({"symbols": len(syms), "chunks": len(chunks), "out": str(out)})


if __name__ == "__main__":
    main()
