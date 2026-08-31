from repoatlas.retrieval.fusion import rrf_fuse


class HybridRetriever:
    def __init__(self, lexical, dense):
        self.lexical = lexical
        self.dense = dense

    def search(self, q: str, lexical_k: int = 40, dense_k: int = 40, fusion_k: int = 30):
        return rrf_fuse(
            [self.lexical.search(q, lexical_k), self.dense.search(q, dense_k)], top_k=fusion_k
        )
