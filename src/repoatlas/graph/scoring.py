def impact_score(
    item,
    graph_distance: int | None = None,
    relationship_weight: float = 0.0,
    test_bonus: float = 0.0,
):
    distance_bonus = 0 if graph_distance is None else 1 / (1 + graph_distance)
    raw = (
        0.25 * item.lexical_score
        + 0.25 * item.dense_score
        + 4 * item.fusion_score
        + 0.35 * item.rerank_score
        + 0.5 * distance_bonus
        + 0.25 * relationship_weight
        + 0.15 * test_bonus
    )
    return float(raw)
