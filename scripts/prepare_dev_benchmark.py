from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from repoatlas.schemas.evaluation import EvaluationCase


def _run(command: list[str]) -> None:
    print("$", " ".join(command))

    subprocess.run(
        command,
        check=True,
    )


def _load_case(path: Path) -> EvaluationCase:
    return EvaluationCase.model_validate_json(path.read_text(encoding="utf-8"))


def _verify_snapshot(
    *,
    case: EvaluationCase,
    snapshot: Path,
) -> None:
    marker = snapshot / ".repoatlas_base_commit"

    if not marker.exists():
        raise RuntimeError(f"{case.case_id}: base marker missing")

    actual_base = marker.read_text(encoding="utf-8").strip()

    if actual_base != case.base_commit:
        raise RuntimeError(
            f"{case.case_id}: snapshot BASE mismatch: {actual_base} != {case.base_commit}"
        )

    git_check = subprocess.run(
        [
            "git",
            "-C",
            str(snapshot),
            "rev-parse",
            "--git-dir",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if git_check.returncode == 0:
        raise RuntimeError(f"{case.case_id}: .git metadata is accessible inside the agent snapshot")

    for file_path in case.expected_changed_files:
        if not (snapshot / file_path).is_file():
            raise RuntimeError(
                f"{case.case_id}: retrieval-gold file is absent from BASE snapshot: {file_path}"
            )


def _verify_processed(
    *,
    case: EvaluationCase,
    processed: Path,
) -> tuple[int, int, int, int]:
    symbols_path = processed / "symbols.json"
    chunks_path = processed / "chunks.json"
    graph_path = processed / "graph.graphml"
    graph_summary_path = processed / "graph_summary.json"

    for path in (
        symbols_path,
        chunks_path,
        graph_path,
        graph_summary_path,
    ):
        if not path.exists():
            raise RuntimeError(f"{case.case_id}: missing artifact: {path}")

    symbols = json.loads(symbols_path.read_text(encoding="utf-8"))

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    graph_summary = json.loads(graph_summary_path.read_text(encoding="utf-8"))

    if not symbols:
        raise RuntimeError(f"{case.case_id}: zero parsed symbols")

    if not chunks:
        raise RuntimeError(f"{case.case_id}: zero parsed chunks")

    available_symbol_keys = {
        (f"{item['file_path']}::{item['qualified_symbol']}") for item in symbols
    }

    missing_gold_symbols = [
        symbol for symbol in case.expected_changed_symbols if symbol not in available_symbol_keys
    ]

    if missing_gold_symbols:
        formatted = "\n".join(f"  - {item}" for item in missing_gold_symbols)

        raise RuntimeError(f"{case.case_id}: gold symbols missing from BASE parsing:\n{formatted}")

    graph_nodes = int(graph_summary.get("nodes", 0))

    graph_edges = int(graph_summary.get("edges", 0))

    if graph_nodes <= 0:
        raise RuntimeError(f"{case.case_id}: graph has no nodes")

    return (
        len(symbols),
        len(chunks),
        graph_nodes,
        graph_edges,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cases-dir",
        default="benchmark/cases",
    )

    parser.add_argument(
        "--repo",
        default="data/repositories/httpx",
    )

    args = parser.parse_args()

    cases_dir = Path(args.cases_dir)
    repo = Path(args.repo)

    case_paths = sorted(cases_dir.glob("httpx-dev-*.json"))

    if not case_paths:
        raise RuntimeError("No HTTPX DEV cases found.")

    results: list[dict[str, object]] = []

    print(f"Preparing {len(case_paths)} HTTPX DEV cases...")

    for case_path in case_paths:
        case = _load_case(case_path)

        snapshot = Path("data/snapshots") / case.case_id

        processed = Path("data/processed") / case.case_id

        print()
        print("=" * 76)
        print(case.case_id)
        print("=" * 76)

        print(
            "BASE:",
            case.base_commit,
        )

        _run(
            [
                sys.executable,
                "-m",
                "scripts.build_snapshot",
                "--repo",
                str(repo),
                "--dest",
                str(snapshot),
                "--base-commit",
                case.base_commit,
            ]
        )

        _verify_snapshot(
            case=case,
            snapshot=snapshot,
        )

        print("SNAPSHOT LEAKAGE CHECK: PASS")

        _run(
            [
                sys.executable,
                "-m",
                "scripts.parse_repository",
                "--repo",
                str(snapshot),
            ]
        )

        _run(
            [
                sys.executable,
                "-m",
                "scripts.build_graph",
                "--repo",
                str(snapshot),
            ]
        )

        (
            symbol_count,
            chunk_count,
            graph_nodes,
            graph_edges,
        ) = _verify_processed(
            case=case,
            processed=processed,
        )

        print("GOLD SYMBOL INTEGRITY: PASS")

        results.append(
            {
                "case_id": case.case_id,
                "base_commit": case.base_commit,
                "retrieval_gold_files": len(case.expected_changed_files),
                "gold_symbols": len(case.expected_changed_symbols),
                "changed_tests": len(case.expected_tests),
                "parsed_symbols": symbol_count,
                "chunks": chunk_count,
                "graph_nodes": graph_nodes,
                "graph_edges": graph_edges,
            }
        )

    output = Path("reports/experiments/httpx-dev-preparation.json")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            {
                "cases": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 76)
    print("HTTPX DEV PREPARATION SUMMARY")
    print("=" * 76)

    header = (
        f"{'Case':<15}"
        f"{'GoldF':>7}"
        f"{'GoldS':>7}"
        f"{'Tests':>7}"
        f"{'Parsed':>9}"
        f"{'Chunks':>9}"
        f"{'Nodes':>9}"
        f"{'Edges':>10}"
    )

    print(header)
    print("-" * len(header))

    for row in results:
        print(
            f"{row['case_id']:<15}"
            f"{row['retrieval_gold_files']:>7}"
            f"{row['gold_symbols']:>7}"
            f"{row['changed_tests']:>7}"
            f"{row['parsed_symbols']:>9}"
            f"{row['chunks']:>9}"
            f"{row['graph_nodes']:>9}"
            f"{row['graph_edges']:>10}"
        )

    print()
    print("MULTI-CASE DEV PREPARATION: PASS")

    print(
        "Report:",
        output,
    )


if __name__ == "__main__":
    main()
