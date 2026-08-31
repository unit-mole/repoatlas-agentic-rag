from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from repoatlas.schemas.evaluation import EvaluationCase

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.STDOUT,
        errors="replace",
    )


def _resolve(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", f"{ref}^{{commit}}").strip()


def _changed_files(
    repo: Path,
    base: str,
    fix: str,
) -> list[str]:
    text = _git(
        repo,
        "diff",
        "--name-only",
        "--diff-filter=ACMRT",
        base,
        fix,
    )
    return [line.strip() for line in text.splitlines() if line.strip()]


def _changed_line_sets(
    repo: Path,
    base: str,
    fix: str,
    path: str,
) -> tuple[set[int], set[int]]:
    """Return old-side and new-side line numbers touched by a patch."""
    patch = _git(
        repo,
        "diff",
        "--unified=0",
        base,
        fix,
        "--",
        path,
    )

    old_changed: set[int] = set()
    new_changed: set[int] = set()

    old_line = 0
    new_line = 0

    for line in patch.splitlines():
        match = _HUNK_RE.match(line)

        if match:
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            continue

        if line.startswith(("+++", "---")):
            continue

        if line.startswith("+"):
            new_changed.add(new_line)
            new_line += 1

        elif line.startswith("-"):
            old_changed.add(old_line)
            old_line += 1

        elif line.startswith(" "):
            old_line += 1
            new_line += 1

    return old_changed, new_changed


def _symbol_spans(
    source: str,
) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    parents: list[str] = []
    spans: list[tuple[int, int, str]] = []

    class Visitor(ast.NodeVisitor):
        def _visit_symbol(
            self,
            node: ast.AST,
            name: str,
        ) -> None:
            start = int(getattr(node, "lineno", 1))
            end = int(getattr(node, "end_lineno", start))

            qualified = ".".join([*parents, name])

            spans.append(
                (
                    start,
                    end,
                    qualified,
                )
            )

            parents.append(name)
            self.generic_visit(node)
            parents.pop()

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self._visit_symbol(
                node,
                node.name,
            )

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            self._visit_symbol(
                node,
                node.name,
            )

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit_symbol(
                node,
                node.name,
            )

    Visitor().visit(tree)

    return spans


def _symbols_overlapping(
    spans: list[tuple[int, int, str]],
    changed_lines: set[int],
) -> list[str]:
    if not changed_lines:
        return []

    hits = [
        (
            end - start,
            name,
        )
        for start, end, name in spans
        if any(start <= line <= end for line in changed_lines)
    ]

    ordered = [
        name
        for _, name in sorted(
            hits,
            key=lambda item: item[0],
        )
    ]

    return list(dict.fromkeys(ordered))


def _source_at(
    repo: Path,
    ref: str,
    path: str,
) -> str | None:
    try:
        return _git(
            repo,
            "show",
            f"{ref}:{path}",
        )
    except subprocess.CalledProcessError:
        return None


def _changed_symbols(
    repo: Path,
    base: str,
    fix: str,
    files: list[str],
) -> list[str]:
    """Create localization gold using only pre-fix-localizable symbols.

    Base-side changed symbols are always valid localization targets.

    Fix-side symbols are included only when the same qualified symbol
    already existed in the base snapshot. This prevents newly introduced
    future symbols from unfairly entering the retrieval denominator.
    """
    symbols: list[str] = []

    for path in files:
        if not path.endswith(".py"):
            continue

        base_source = _source_at(
            repo,
            base,
            path,
        )

        if base_source is None:
            continue

        fix_source = _source_at(
            repo,
            fix,
            path,
        )

        old_lines, new_lines = _changed_line_sets(
            repo,
            base,
            fix,
            path,
        )

        base_spans = _symbol_spans(base_source)

        base_names = {name for _, _, name in base_spans}

        for symbol in _symbols_overlapping(
            base_spans,
            old_lines,
        ):
            symbols.append(f"{path}::{symbol}")

        if fix_source is not None:
            fix_spans = _symbol_spans(fix_source)

            for symbol in _symbols_overlapping(
                fix_spans,
                new_lines,
            ):
                if symbol in base_names:
                    symbols.append(f"{path}::{symbol}")

    return list(dict.fromkeys(symbols))


def _localizable_changed_files(
    repo: Path,
    base: str,
    files: list[str],
) -> tuple[list[str], list[str]]:
    """Split Git changes into retrievable and provenance-only files.

    Current RepoAtlas retrieval operates on Python class/function symbol
    chunks. A changed file is therefore retrieval-localizable only when:

    1. it is Python,
    2. it exists in the pre-fix BASE snapshot, and
    3. BASE contains at least one class/function/async-function symbol.

    Everything else remains historical provenance but is excluded from
    the retrieval metric denominator.
    """
    localizable: list[str] = []
    excluded: list[str] = []

    for file_path in files:
        if not file_path.endswith(".py"):
            excluded.append(file_path)
            continue

        source = _source_at(
            repo,
            base,
            file_path,
        )

        if source is None:
            excluded.append(file_path)
            continue

        if not _symbol_spans(source):
            excluded.append(file_path)
            continue

        localizable.append(file_path)

    return localizable, excluded


@dataclass(frozen=True)
class HistoricalCaseBuild:
    case: EvaluationCase
    gold_patch: str


def build_historical_case(
    *,
    repo: Path,
    repository_name: str,
    fix_commit: str,
    issue_text: str,
    case_id: str,
    split: str = "dev",
    difficulty: str = "medium",
    category: str = "bug_localization",
) -> HistoricalCaseBuild:
    """Build evaluator gold from a historical fix.

    Agent execution is frozen at the parent of the fix commit.
    The gold patch remains evaluator-only.
    """
    repo = repo.resolve()

    fix = _resolve(
        repo,
        fix_commit,
    )

    base = _resolve(
        repo,
        f"{fix}^",
    )

    all_files = _changed_files(
        repo,
        base,
        fix,
    )

    files, excluded_files = _localizable_changed_files(
        repo,
        base,
        all_files,
    )

    symbols = _changed_symbols(
        repo,
        base,
        fix,
        files,
    )

    tests = [
        path
        for path in files
        if path.startswith(
            (
                "tests/",
                "test/",
            )
        )
        or Path(path).name.startswith("test_")
    ]

    patch = _git(
        repo,
        "diff",
        "--binary",
        base,
        fix,
    )

    case = EvaluationCase(
        case_id=case_id,
        repository=repository_name,
        base_commit=base,
        issue_text=issue_text,
        all_changed_files=all_files,
        expected_changed_files=files,
        excluded_changed_files=excluded_files,
        expected_changed_symbols=symbols,
        expected_tests=tests,
        gold_patch=None,
        fix_commit=fix,
        difficulty=difficulty,
        category=category,
        split=split,
    )

    return HistoricalCaseBuild(
        case=case,
        gold_patch=patch,
    )


def write_historical_case(
    build: HistoricalCaseBuild,
    cases_dir: Path,
    gold_dir: Path,
) -> tuple[Path, Path]:
    cases_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    gold_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    case_path = cases_dir / f"{build.case.case_id}.json"

    gold_path = gold_dir / f"{build.case.case_id}.patch"

    case_path.write_text(
        json.dumps(
            build.case.model_dump(),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    gold_path.write_text(
        build.gold_patch,
        encoding="utf-8",
    )

    return case_path, gold_path


def make_case(**kwargs) -> EvaluationCase:
    """Construct a validated case when gold labels are already known."""
    return EvaluationCase(**kwargs)
