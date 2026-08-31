class HeuristicReranker:
    def rerank(self, query, items, top_k=12):
        q = set(query.lower().split())
        for x in items:
            toks = set((x.qualified_symbol + " " + x.content).lower().split())
            x.rerank_score = len(q & toks) / max(len(q), 1) + x.fusion_score
        return sorted(items, key=lambda x: x.rerank_score, reverse=True)[:top_k]


class BGEReranker:
    def __init__(self, model_name="BAAI/bge-reranker-v2-m3"):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(self, query, items, top_k=12):
        if not items:
            return []
        scores = self.model.predict([(query, x.qualified_symbol + "\n" + x.content) for x in items])
        for x, s in zip(items, scores):
            x.rerank_score = float(s)
        return sorted(items, key=lambda x: x.rerank_score, reverse=True)[:top_k]
