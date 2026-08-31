def graph_metrics(initial: set[str], expanded: set[str], gold: set[str]):
    added = expanded - initial
    relevant = added & gold
    return {
        "graph_added_relevant_recall": len(relevant) / max(len(gold - initial), 1),
        "graph_neighbor_precision": len(relevant) / max(len(added), 1),
        "irrelevant_expansion_rate": len(added - relevant) / max(len(added), 1),
        "average_graph_nodes_added": len(added),
    }
