from __future__ import annotations

from pathlib import Path

import numpy as np

from repoatlas.schemas.symbols import CodeChunk


class QdrantVectorStore:
    """Thin direct-Qdrant adapter with URL or embedded/local persistence modes."""

    def __init__(
        self,
        collection: str,
        dimensions: int,
        *,
        url: str | None = None,
        local_path: Path | None = None,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        if bool(url) == bool(local_path):
            raise ValueError("Provide exactly one of url or local_path")
        self.collection = collection
        self.client = QdrantClient(url=url) if url else QdrantClient(path=str(local_path))
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )

    def upsert(self, chunks: list[CodeChunk], vectors: np.ndarray) -> None:
        from qdrant_client.models import PointStruct

        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector.astype(float).tolist(),
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "repository_id": chunk.repository_id,
                        "file_path": chunk.file_path,
                        "qualified_symbol": chunk.qualified_symbol,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "content": chunk.content,
                    },
                )
            )
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, vector: np.ndarray, limit: int = 20) -> list[dict]:
        hits = self.client.query_points(
            collection_name=self.collection,
            query=vector.astype(float).tolist(),
            limit=limit,
            with_payload=True,
        ).points
        return [{"score": float(hit.score), "payload": dict(hit.payload or {})} for hit in hits]
