import subprocess
from pathlib import Path

from benchmark.builders.historical import build_historical_case


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message], check=True, capture_output=True
    )
    return _git(repo, "rev-parse", "HEAD")


def test_historical_builder_separates_gold_patch(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "src").mkdir()
    target = repo / "src" / "demo.py"
    target.write_text("def timeout():\n    return 10\n", encoding="utf-8")
    base = _commit(repo, "base")
    target.write_text("def timeout():\n    return 20\n", encoding="utf-8")
    fix = _commit(repo, "fix timeout")

    build = build_historical_case(
        repo=repo,
        repository_name="fixture",
        fix_commit=fix,
        issue_text="Increase timeout",
        case_id="fixture-001",
    )
    assert build.case.base_commit == base
    assert build.case.fix_commit == fix
    assert build.case.expected_changed_files == ["src/demo.py"]
    assert any("timeout" in symbol for symbol in build.case.expected_changed_symbols)
    assert build.case.gold_patch is None
    assert "return 20" in build.gold_patch
