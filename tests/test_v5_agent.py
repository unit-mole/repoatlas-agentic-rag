from types import SimpleNamespace

import networkx as nx

from repoatlas.agents.v5 import (
    V5InvestigationAgent,
)


class FakeHybrid:
    def __init__(
        self,
        hits,
    ):
        self.hits = hits

    def search(
        self,
        _query,
    ):
        return self.hits


class FakeProvider:
    def __init__(self):
        self.user_prompt = ""

    def complete(
        self,
        _system,
        user,
        temperature=0.1,
        max_tokens=1200,
    ):
        self.user_prompt = user
        return (
            "Likely change location is supported "
            "by direct evidence [D1] and related "
            "test evidence [T1]."
        )


def test_v5_uses_frozen_evidence_pipeline(
    tmp_path,
):
    repo = tmp_path / "repo"
    repo.mkdir()

    (
        repo
        / ".repoatlas_base_commit"
    ).write_text(
        "abc123\n",
        encoding="utf-8",
    )

    hit = SimpleNamespace(
        chunk_id="chunk-1",
        file_path="src/mod.py",
        qualified_symbol="pkg.func",
        fusion_score=0.9,
        evidence="def func(): pass",
    )

    graph = nx.MultiDiGraph()

    source_node = (
        "sym:src/mod.py:pkg.func"
    )

    test_node = (
        "sym:tests/test_mod.py:"
        "test_func"
    )

    graph.add_node(
        source_node,
        type="symbol",
        file_path="src/mod.py",
        symbol="pkg.func",
    )

    graph.add_node(
        test_node,
        type="symbol",
        file_path="tests/test_mod.py",
        symbol="test_func",
    )

    graph.add_edge(
        test_node,
        source_node,
        relationship="TESTS",
        confidence=1.0,
    )

    runtime = {
        "hybrid": FakeHybrid(
            [hit]
        ),
        "graph": graph,
    }

    provider = FakeProvider()

    agent = V5InvestigationAgent(
        repo=repo,
        runtime=runtime,
        provider=provider,
    )

    result = agent.investigate(
        "Fix pkg.func behavior."
    )

    assert (
        result["agent_version"]
        == "V5"
    )

    assert (
        result["base_commit"]
        == "abc123"
    )

    assert (
        result[
            "likely_affected_files"
        ][0]
        == "src/mod.py"
    )

    assert (
        result["related_tests"][0]
        == "tests/test_mod.py"
    )

    assert (
        result[
            "retrieval"
        ]["v3s_default"]
        is False
    )

    assert (
        "[D1]"
        in result[
            "investigation_report"
        ]
    )

    assert (
        "[T1]"
        in result[
            "investigation_report"
        ]
    )

    assert (
        "expected_changed"
        not in provider.user_prompt
    )
