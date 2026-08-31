def pr(pred, gold):
    p = set(pred)
    g = set(gold)
    tp = len(p & g)
    return {
        "precision": tp / max(len(p), 1),
        "recall": tp / max(len(g), 1),
        "unnecessary_rate": len(p - g) / max(len(p), 1),
    }
