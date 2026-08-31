import argparse
import json
from pathlib import Path

from repoatlas.evaluation.failure_analysis import summarize_failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reports/experiments/case_outcomes.json")
    args = parser.parse_args()
    source = Path(args.input)
    rows = json.loads(source.read_text(encoding="utf-8")) if source.exists() else []
    summary = summarize_failures(rows)
    out = Path("reports/failure_analysis/failure_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
