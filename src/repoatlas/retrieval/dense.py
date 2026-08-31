import numpy as np

from repoatlas.schemas.retrieval import RetrievedCode
from repoatlas.schemas.symbols import CodeChunk


class DenseIndex:
    def __init__(self, chunks: list[CodeChunk], provider):
        self.chunks = chunks
        self.provider = provider
        texts = [
            c.qualified_symbol + "\n" + c.signature + "\n" + c.docstring + "\n" + c.content
            for c in chunks
        ]
        self.matrix = provider.encode(texts) if texts else np.zeros((0, 1), dtype=np.float32)

    def search(self, q: str, top_k: int = 40):
        if len(self.chunks) == 0:
            return []
        v = self.provider.encode([q])[0]
        scores = self.matrix @ v
        ids = np.argsort(-scores)[:top_k]
        out = []
        for i in ids:
            c = self.chunks[int(i)]
            out.append(
                RetrievedCode(
                    chunk_id=c.chunk_id,
                    file_path=c.file_path,
                    qualified_symbol=c.qualified_symbol,
                    content=c.content,
                    dense_score=float(scores[int(i)]),
                    evidence=[
                        f"[SYM: {c.qualified_symbol}]",
                        f"[SRC: {c.file_path}:L{c.start_line}-L{c.end_line}]",
                    ],
                )
            )
        return out
