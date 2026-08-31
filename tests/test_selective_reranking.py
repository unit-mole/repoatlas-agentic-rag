from repoatlas.reranking.selective import (
    merge_symbol_ranking,
    select_symbol_candidates,
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


def test_selects_symbols_from_top_files_only():
    hits = [
        _hit("a.py", "a1"),
        _hit("b.py", "b1"),
        _hit("c.py", "c1"),
        _hit("a.py", "a2"),
        _hit("b.py", "b2"),
        _hit("a.py", "a3"),
    ]

    selected = select_symbol_candidates(
        hits,
        file_limit=2,
        candidate_limit=4,
    )

    assert [
        (
            item.file_path,
            item.qualified_symbol,
        )
        for item in selected
    ] == [
        ("a.py", "a1"),
        ("b.py", "b1"),
        ("a.py", "a2"),
        ("b.py", "b2"),
    ]


def test_candidate_limit_is_respected():
    hits = [
        _hit("a.py", "a1"),
        _hit("a.py", "a2"),
        _hit("a.py", "a3"),
        _hit("a.py", "a4"),
    ]

    selected = select_symbol_candidates(
        hits,
        file_limit=1,
        candidate_limit=2,
    )

    assert len(selected) == 2


def test_merge_preserves_unselected_v2_symbols():
    original = [
        _hit("a.py", "a1"),
        _hit("a.py", "a2"),
        _hit("b.py", "b1"),
        _hit("c.py", "c1"),
    ]

    reranked = [
        original[1],
        original[0],
    ]

    result = merge_symbol_ranking(
        reranked,
        original,
    )

    assert result == [
        "a.py::a2",
        "a.py::a1",
        "b.py::b1",
        "c.py::c1",
    ]
