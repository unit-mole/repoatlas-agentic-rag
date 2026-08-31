from repoatlas.schemas.retrieval import RetrievedCode


def rrf_fuse(lists: list[list[RetrievedCode]], k: int = 60, top_k: int = 30) -> list[RetrievedCode]:
    merged = {}
    scores = {}
    for results in lists:
        for rank, item in enumerate(results, 1):
            merged.setdefault(item.chunk_id, item)
            scores[item.chunk_id] = scores.get(item.chunk_id, 0) + 1 / (k + rank)
    out = []
    for cid in sorted(scores, key=scores.get, reverse=True)[:top_k]:
        x = merged[cid].model_copy(deep=True)
        x.fusion_score = scores[cid]
        out.append(x)
    return out
