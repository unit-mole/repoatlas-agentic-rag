import argparse
import subprocess
from pathlib import Path

from repoatlas.schemas.evaluation import EvaluationCase


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/evaluation")
    parser.add_argument("--repo", default="data/fixture_repo")
    args = parser.parse_args()

    errors = []
    count = 0

    for path in Path(args.cases).rglob("*.json"):
        case = EvaluationCase.model_validate_json(path.read_text())
        count += 1

        try:
            subprocess.run(
                [
                    "git",
                    "-C",
                    args.repo,
                    "cat-file",
                    "-e",
                    f"{case.base_commit}^{{commit}}",
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            errors.append(f"{case.case_id}: base commit unavailable")

        if case.fix_commit and case.gold_patch and case.gold_patch in case.issue_text:
            errors.append(f"{case.case_id}: gold patch leaked into issue")

    print(
        {
            "cases": count,
            "errors": errors,
            "ok": not errors,
        }
    )

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
