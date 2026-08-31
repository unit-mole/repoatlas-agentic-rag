from __future__ import annotations

import argparse
from pathlib import Path

from benchmark.builders.historical import build_historical_case, write_historical_case


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a leakage-controlled issue→fix benchmark case."
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--repository-name", required=True)
    parser.add_argument("--fix-commit", required=True)
    parser.add_argument("--issue-text", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--difficulty", default="medium")
    parser.add_argument("--category", default="bug_localization")
    parser.add_argument("--cases-dir", type=Path, default=Path("benchmark/cases"))
    parser.add_argument("--gold-dir", type=Path, default=Path("benchmark/gold"))
    args = parser.parse_args()

    build = build_historical_case(
        repo=args.repo,
        repository_name=args.repository_name,
        fix_commit=args.fix_commit,
        issue_text=args.issue_text,
        case_id=args.case_id,
        split=args.split,
        difficulty=args.difficulty,
        category=args.category,
    )
    case_path, gold_path = write_historical_case(build, args.cases_dir, args.gold_dir)
    print(f"base_commit={build.case.base_commit}")
    print(f"fix_commit={build.case.fix_commit}")
    print(f"changed_files={len(build.case.expected_changed_files)}")
    print(f"changed_symbols={len(build.case.expected_changed_symbols)}")
    print(f"case={case_path}")
    print(f"gold={gold_path} (evaluator-only; never mount into agent sandbox)")


if __name__ == "__main__":
    main()
