def recall_at_k(pred: list[str], gold: list[str], k: int):
    g = set(gold)
    return 1.0 if not g else len(set(pred[:k]) & g) / len(g)


def precision_at_k(pred: list[str], gold: list[str], k: int):
    return len(set(pred[:k]) & set(gold)) / max(k, 1)


def mrr(pred: list[str], gold: list[str]):
    g = set(gold)
    for i, x in enumerate(pred, 1):
        if x in g:
            return 1 / i
    return 0.0


def ndcg_at_k(pred: list[str], gold: list[str], k: int):
    import math

    g = set(gold)
    dcg = sum((1 if x in g else 0) / math.log2(i + 2) for i, x in enumerate(pred[:k]))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(g), k)))
    return dcg / ideal if ideal else 1.0
