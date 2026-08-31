import subprocess
from pathlib import Path

from repoatlas.schemas.evaluation import EvaluationCase


def main():
    repo = Path("data/fixture_repo")
    commit = (
        subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if repo.exists()
        else "FIXTURE_BASE_COMMIT_AFTER_CREATE_FIXTURE"
    )
    case = EvaluationCase(
        case_id="fixture-cache-001",
        repository="fixture_repo",
        base_commit=commit,
        issue_text="Changing cache timeout behavior may affect token refresh. Find affected implementation and tests.",
        expected_changed_files=["src/demo/cache.py", "src/demo/auth.py", "tests/test_auth.py"],
        expected_changed_symbols=["Cache", "TokenManager.refresh_token", "test_refresh_uses_cache"],
        expected_tests=["test_refresh_uses_cache"],
        difficulty="easy",
        category="graph_heavy",
        split="dev",
    )
    p = Path("data/evaluation/dev")
    p.mkdir(parents=True, exist_ok=True)
    (p / "fixture-cache-001.json").write_text(case.model_dump_json(indent=2))
    print(p / "fixture-cache-001.json")


if __name__ == "__main__":
    main()
