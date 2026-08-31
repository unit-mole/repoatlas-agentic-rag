from pathlib import Path

from repoatlas.pipeline import build_runtime


def test_fixture_like_runtime(tmp_path: Path):
    (tmp_path / "x.py").write_text(
        "def cache_timeout(): return 30\ndef refresh_token(): return cache_timeout()\n",
        encoding="utf-8",
    )
    runtime = build_runtime(tmp_path)
    result = runtime["engine"].investigate("cache timeout token refresh", 1)
    assert result["likely_affected_files"]
