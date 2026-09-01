import pytest

from repoatlas.agents.v6 import (
    V6SafeCodingAgent,
)


def test_v6_write_is_disabled_by_default(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv(
        "ENABLE_WRITE_TOOLS",
        raising=False,
    )

    repo = tmp_path / "repo"
    repo.mkdir()

    agent = V6SafeCodingAgent(
        source_snapshot=repo,
        runtime={},
        provider=object(),
        v5_report={},
        workspaces_root=(tmp_path / "workspaces"),
    )

    with pytest.raises(
        PermissionError,
        match="ENABLE_WRITE_TOOLS",
    ):
        agent.run("Change something.")


def test_v6_rejects_mismatched_v5_base(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "ENABLE_WRITE_TOOLS",
        "true",
    )

    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / ".repoatlas_base_commit").write_text(
        "base-a\n",
        encoding="utf-8",
    )

    agent = V6SafeCodingAgent(
        source_snapshot=repo,
        runtime={},
        provider=object(),
        v5_report={"base_commit": "base-b"},
        workspaces_root=(tmp_path / "workspaces"),
    )

    with pytest.raises(
        ValueError,
        match="BASE",
    ):
        agent.run("Change something.")
