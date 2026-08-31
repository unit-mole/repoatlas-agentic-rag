from __future__ import annotations

import argparse
import json
from pathlib import Path

from repoatlas.embeddings.bge import BGEEmbeddingProvider, HashEmbeddingProvider
from repoatlas.parsing.chunks import symbols_to_chunks
from repoatlas.parsing.symbols import extract_repository_symbols
from repoatlas.retrieval.qdrant_store import QdrantVectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--embedding", choices=["hash", "bge"], default="bge")
    parser.add_argument("--mode", choices=["embedded", "url"], default="embedded")
    parser.add_argument("--url", default="http://localhost:6333")
    parser.add_argument("--local-path", default="data/qdrant_embedded")
    args = parser.parse_args()

    repo = Path(args.repo)
    symbols = extract_repository_symbols(repo.name, repo)
    chunks = symbols_to_chunks(symbols)
    provider = HashEmbeddingProvider() if args.embedding == "hash" else BGEEmbeddingProvider()
    texts = [
        c.qualified_symbol + "\n" + c.signature + "\n" + c.docstring + "\n" + c.content
        for c in chunks
    ]
    vectors = provider.encode(texts)
    store = QdrantVectorStore(
        collection=f"repoatlas_{repo.name}",
        dimensions=int(vectors.shape[1]),
        url=args.url if args.mode == "url" else None,
        local_path=Path(args.local_path) if args.mode == "embedded" else None,
    )
    store.upsert(chunks, vectors)
    result = {
        "collection": f"repoatlas_{repo.name}",
        "mode": args.mode,
        "embedding": args.embedding,
        "points": len(chunks),
        "dimensions": int(vectors.shape[1]),
    }
    out = Path("data/processed") / repo.name / "qdrant_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
