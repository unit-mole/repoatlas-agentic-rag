from pathlib import Path

from repoatlas.graph.builder import RepositoryGraphBuilder
from repoatlas.parsing.symbols import extract_repository_symbols


def test_graph_build(tmp_path: Path):
    (tmp_path / "a.py").write_text("def b(): return 1\ndef a(): return b()\n", encoding="utf-8")
    symbols = extract_repository_symbols("r", tmp_path)
    graph = RepositoryGraphBuilder(symbols).build(tmp_path)
    assert any(data.get("relationship") == "CALLS" for *_, data in graph.edges(data=True))
