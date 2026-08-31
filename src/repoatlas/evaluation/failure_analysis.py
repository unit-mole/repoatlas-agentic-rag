from __future__ import annotations

from collections import Counter

FAILURE_TYPES = {
    "lexical_retrieval_miss",
    "semantic_retrieval_miss",
    "reranker_failure",
    "graph_under_expansion",
    "graph_over_expansion",
    "wrong_symbol",
    "wrong_file",
    "wrong_test",
    "issue_misunderstanding",
    "bad_change_plan",
    "hallucinated_api",
    "patch_syntax_error",
    "target_test_failure",
    "regression_failure",
    "unrelated_change",
    "tool_failure",
    "sandbox_failure",
    "agent_loop",
    "timeout",
    "context_overflow",
    "prompt_injection",
}


def summarize_failures(rows: list[dict]) -> dict:
    counts = Counter()
    examples: dict[str, list[str]] = {}
    for row in rows:
        failure = row.get("failure_type")
        if not failure:
            continue
        if failure not in FAILURE_TYPES:
            failure = "tool_failure"
        counts[failure] += 1
        examples.setdefault(failure, []).append(str(row.get("case_id", "unknown")))
    return {"counts": dict(counts), "examples": examples}
