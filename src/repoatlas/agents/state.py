from typing import TypedDict


class AgentState(TypedDict, total=False):
    task_id: str
    repository_id: str
    base_commit: str
    user_request: str
    task_type: str
    identifiers: list[str]
    investigation_plan: list[str]
    search_queries: list[str]
    retrieved_symbols: list[dict]
    graph_seeds: list[str]
    graph_evidence: list[dict]
    candidate_files: list[str]
    candidate_symbols: list[str]
    impact_scores: dict[str, float]
    selected_tests: list[str]
    change_plan: dict
    workspace_id: str
    patch: str
    test_results: dict
    lint_results: dict
    static_results: dict
    verification_result: dict
    retry_count: int
    tool_count: int
    retrieval_cycles: int
    approval_state: str
    activity_timeline: list[str]
    final_report: dict
