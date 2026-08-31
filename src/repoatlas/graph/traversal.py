import networkx as nx


def expand(graph: nx.MultiDiGraph, seeds: list[str], max_hops: int = 2, max_added_nodes: int = 25):
    seen = set(seeds)
    frontier = set(seeds)
    evidence = []
    for hop in range(1, max_hops + 1):
        nxt = set()
        for n in frontier:
            if n not in graph:
                continue
            for u, v, d in list(graph.in_edges(n, data=True)) + list(graph.out_edges(n, data=True)):
                other = u if v == n else v
                if other not in seen:
                    nxt.add(other)
                    evidence.append(
                        {
                            "source": u,
                            "target": v,
                            "relationship": d.get("relationship"),
                            "hop": hop,
                            "confidence": d.get("confidence", 1.0),
                        }
                    )
                if len(seen | nxt) >= len(seeds) + max_added_nodes:
                    break
        seen |= nxt
        frontier = nxt
        if not frontier or len(seen) >= len(seeds) + max_added_nodes:
            break
    return list(seen), evidence
