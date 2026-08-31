import hashlib

import numpy as np


class HashEmbeddingProvider:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        arr = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in t.lower().split():
                h = int(hashlib.sha256(tok.encode()).hexdigest()[:16], 16)
                arr[i, h % self.dim] += 1.0
            n = np.linalg.norm(arr[i])
            arr[i] /= n if n else 1
        return arr


class BGEEmbeddingProvider:
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name, device=device)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )
