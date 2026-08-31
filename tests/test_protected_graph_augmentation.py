import networkx as nx

from repoatlas.graph.protected_augmentation import (
    protected_graph_augmentation,
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


def _add_symbol(
    graph: nx.MultiDiGraph,
    file_path: str,
    symbol: str,
) -> str:
    node = f"sym:{file_path}:{symbol}"

    graph.add_node(
        node,
        type="symbol",
        file_path=file_path,
        symbol=symbol,
    )

    return node


def test_protected_graph_preserves_direct_prefix():
    graph = nx.MultiDiGraph()

    a = _add_symbol(
        graph,
        "src/a.py",
        "a",
    )

    _add_symbol(
        graph,
        "src/b.py",
        "b",
    )

    _add_symbol(
        graph,
        "src/c.py",
        "c",
    )

    _add_symbol(
        graph,
        "src/d.py",
        "d",
    )

    graph_symbol = _add_symbol(
        graph,
        "src/graph.py",
        "related",
    )

    graph.add_edge(
        a,
        graph_symbol,
        relationship="CALLS",
        confidence=1.0,
    )

    hits = [
        _hit("src/a.py", "a"),
        _hit("src/b.py", "b"),
        _hit("src/c.py", "c"),
        _hit("src/d.py", "d"),
    ]

    result = protected_graph_augmentation(
        direct_hits=hits,
        graph=graph,
        max_hops=1,
        seed_limit=1,
        protected_symbol_k=2,
        protected_file_k=2,
    )

    assert result.symbols[:2] == [
        "src/a.py::a",
        "src/b.py::b",
    ]

    assert result.files[:2] == [
        "src/a.py",
        "src/b.py",
    ]

    assert result.symbols[2] == "src/graph.py::related"

    assert result.protected_prefix_size == 2


def test_protected_graph_is_deterministic():
    graph = nx.MultiDiGraph()

    source = _add_symbol(
        graph,
        "src/source.py",
        "source",
    )

    first = _add_symbol(
        graph,
        "src/a.py",
        "a",
    )

    second = _add_symbol(
        graph,
        "src/b.py",
        "b",
    )

    graph.add_edge(
        source,
        second,
        relationship="CALLS",
        confidence=1.0,
    )

    graph.add_edge(
        source,
        first,
        relationship="CALLS",
        confidence=1.0,
    )

    hits = [
        _hit(
            "src/source.py",
            "source",
        )
    ]

    one = protected_graph_augmentation(
        direct_hits=hits,
        graph=graph,
        protected_symbol_k=1,
        protected_file_k=1,
    )

    two = protected_graph_augmentation(
        direct_hits=hits,
        graph=graph,
        protected_symbol_k=1,
        protected_file_k=1,
    )

    assert one.files == two.files
    assert one.symbols == two.symbols
    assert one.graph_candidates == two.graph_candidates


def test_graph_fills_after_short_direct_file_prefix():
    graph = nx.MultiDiGraph()

    source_a = _add_symbol(
        graph,
        "src/a.py",
        "a1",
    )

    _add_symbol(
        graph,
        "src/a.py",
        "a2",
    )

    _add_symbol(
        graph,
        "src/a.py",
        "a3",
    )

    _add_symbol(
        graph,
        "src/b.py",
        "b1",
    )

    graph_only = _add_symbol(
        graph,
        "src/graph.py",
        "related",
    )

    graph.add_edge(
        source_a,
        graph_only,
        relationship="CALLS",
        confidence=1.0,
    )

    hits = [
        _hit(
            "src/a.py",
            "a1",
        ),
        _hit(
            "src/a.py",
            "a2",
        ),
        _hit(
            "src/a.py",
            "a3",
        ),
        _hit(
            "src/b.py",
            "b1",
        ),
    ]

    result = protected_graph_augmentation(
        direct_hits=hits,
        graph=graph,
        max_hops=1,
        seed_limit=1,
        protected_symbol_k=10,
        protected_file_k=10,
    )

    direct_files = [
        "src/a.py",
        "src/b.py",
    ]

    assert result.files[: len(direct_files)] == direct_files

    assert result.files[2] == ("src/graph.py")

    assert result.symbols[:4] == [
        "src/a.py::a1",
        "src/a.py::a2",
        "src/a.py::a3",
        "src/b.py::b1",
    ]
