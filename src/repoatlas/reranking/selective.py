from __future__ import annotations

from repoatlas.schemas.retrieval import RetrievedCode


def symbol_key(
    item: RetrievedCode,
) -> str:
    return f"{item.file_path}::{item.qualified_symbol}"


def select_symbol_candidates(
    hits: list[RetrievedCode],
    *,
    file_limit: int = 5,
    candidate_limit: int = 12,
) -> list[RetrievedCode]:
    """Select a small symbol pool from strongest V2 files."""

    if file_limit <= 0 or candidate_limit <= 0 or not hits:
        return []

    selected_files: list[str] = []

    for item in hits:
        if item.file_path not in selected_files:
            selected_files.append(item.file_path)

        if len(selected_files) >= file_limit:
            break

    allowed_files = set(selected_files)

    candidates: list[RetrievedCode] = []
    seen: set[str] = set()

    for item in hits:
        if item.file_path not in allowed_files:
            continue

        key = symbol_key(item)

        if key in seen:
            continue

        seen.add(key)
        candidates.append(item)

        if len(candidates) >= candidate_limit:
            break

    return candidates


def merge_symbol_ranking(
    reranked: list[RetrievedCode],
    original: list[RetrievedCode],
) -> list[str]:
    """Put reranked candidates first, then preserve V2 remainder."""

    result: list[str] = []
    seen: set[str] = set()

    for item in reranked:
        key = symbol_key(item)

        if key not in seen:
            result.append(key)
            seen.add(key)

    for item in original:
        key = symbol_key(item)

        if key not in seen:
            result.append(key)
            seen.add(key)

    return result
