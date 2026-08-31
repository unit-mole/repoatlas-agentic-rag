import networkx as nx

from repoatlas.graph.test_discovery import (
    discover_related_tests,
)
from repoatlas.schemas.retrieval import RetrievedCode


def _hit(
    file_path: str,
    symbol: str,
) -> RetrievedCode:
    return RetrievedCode(
        chunk_id=f"{file_path}:{symbol}",
        file_path=file_path,
        qualified_symbol=symbol,
        content="demo",
    )


def test_discovers_tests_from_reverse_tests_edges():
    graph = nx.MultiDiGraph()

    source = "sym:src/client.py:Client"

    test_a = "sym:tests/test_client.py:test_client"

    test_b = "sym:tests/test_other.py:test_other"

    graph.add_node(
        source,
        type="symbol",
        file_path="src/client.py",
        symbol="Client",
    )

    graph.add_node(
        test_a,
        type="symbol",
        file_path="tests/test_client.py",
        symbol="test_client",
    )

    graph.add_node(
        test_b,
        type="symbol",
        file_path="tests/test_other.py",
        symbol="test_other",
    )

    graph.add_edge(
        test_a,
        source,
        relationship="TESTS",
        confidence=0.9,
    )

    graph.add_edge(
        test_b,
        source,
        relationship="TESTS",
        confidence=0.9,
    )

    results = discover_related_tests(
        graph,
        [_hit("src/client.py", "Client")],
    )

    paths = [candidate.file_path for candidate in results]

    assert "tests/test_client.py" in paths
    assert "tests/test_other.py" in paths

    assert results[0].best_source_rank == 1
    assert results[0].supporting_edges >= 1
