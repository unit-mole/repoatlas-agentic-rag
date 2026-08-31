from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from repoatlas.agents.planner import classify_task, extract_identifiers, plan
from repoatlas.graph.traversal import expand


class InvestigationEngine:
    """Bounded repository-investigation engine used by both direct and LangGraph modes.

    Retrieval and graph traversal stay deterministic. An LLM may be layered on top for
    concise explanation, but tool selection, cutoff rules, and stopping remain code.
    """

    def __init__(self, retriever, reranker, graph, chunks):
        self.retriever = retriever
        self.reranker = reranker
        self.graph = graph
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}

    def retrieve(self, query: str, top_k: int = 12):
        hits = self.retriever.search(query)
        return self.reranker.rerank(query, hits, top_k)

    def graph_expand(self, hits, graph_hops: int = 2):
        symbol_to_node = {
            data.get("symbol"): node
            for node, data in self.graph.nodes(data=True)
            if data.get("type") == "symbol"
        }
        seeds = [
            symbol_to_node[item.qualified_symbol]
            for item in hits
            if item.qualified_symbol in symbol_to_node
        ][:5]
        nodes, evidence = expand(self.graph, seeds, graph_hops, 25)
        return seeds, nodes, evidence

    @staticmethod
    def _refine_query(request: str, identifiers: list[str], hits, cycle: int) -> str:
        parts = [request]
        if identifiers:
            parts.append("exact identifiers: " + " ".join(identifiers[:6]))
        if hits:
            parts.append("candidate symbols: " + " ".join(x.qualified_symbol for x in hits[:4]))
        parts.append(f"investigation refinement {cycle}")
        return "\n".join(parts)

    @staticmethod
    def _evidence_sufficient(hits, evidence, cycle: int, max_cycles: int) -> bool:
        # Conservative bounded rule: require several direct candidates, or one direct
        # candidate plus graph support. Always stop at the configured cycle ceiling.
        if cycle >= max_cycles:
            return True
        if len(hits) >= 3:
            return True
        return bool(hits and evidence)

    def _report_from_hits(
        self,
        *,
        task_id: str,
        request: str,
        hits,
        evidence: list[dict[str, Any]],
        graph_nodes: list[str],
        timeline: list[str],
        retrieval_cycles: int,
        tool_count: int,
    ) -> dict[str, Any]:
        files: defaultdict[str, float] = defaultdict(float)
        symbols: list[dict[str, Any]] = []
        tests: list[str] = []
        for rank, item in enumerate(hits, 1):
            item.impact_relevance_score = (
                (1 / rank) + 4 * item.fusion_score + 0.5 * item.rerank_score
            )
            files[item.file_path] = max(files[item.file_path], item.impact_relevance_score)
            symbols.append(
                {
                    "symbol": item.qualified_symbol,
                    "file": item.file_path,
                    "score": round(item.impact_relevance_score, 4),
                    "evidence": item.evidence,
                }
            )
            if item.file_path.startswith("tests/") or "test_" in item.qualified_symbol:
                tests.append(item.qualified_symbol)

        for node in graph_nodes:
            data = self.graph.nodes[node]
            if data.get("type") == "symbol" and data.get("file_path", "").startswith("tests/"):
                tests.append(data.get("symbol"))

        return {
            "task_id": task_id,
            "task_type": classify_task(request),
            "identifiers": extract_identifiers(request),
            "investigation_plan": plan(request),
            "issue_summary": request,
            "likely_affected_files": [
                {"file": path, "score": round(score, 4)}
                for path, score in sorted(files.items(), key=lambda pair: pair[1], reverse=True)
            ],
            "likely_primary_symbols": symbols,
            "dependency_evidence": evidence,
            "related_tests": list(dict.fromkeys(test for test in tests if test))[:20],
            "risk_areas": [
                "graph edges are conservative static approximations",
                "dynamic dispatch and runtime configuration may require manual review",
            ],
            "recommended_change_plan": [
                "inspect top-ranked symbols and direct graph neighbors",
                "run focused tests before broader package tests",
                "only enable write mode after read-only evidence is accepted",
            ],
            "confidence_label": "evidence-backed relevance, not calibrated probability",
            "uncertain_areas": []
            if hits
            else ["No sufficiently relevant repository evidence was retrieved."],
            "retrieval_cycles": retrieval_cycles,
            "tool_count": tool_count,
            "activity_timeline": timeline,
        }

    def investigate(
        self,
        request: str,
        graph_hops: int = 2,
        top_k: int = 12,
        max_retrieval_cycles: int = 3,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        identifiers = extract_identifiers(request)
        query = request
        accumulated: dict[str, Any] = {}
        evidence: list[dict[str, Any]] = []
        graph_nodes: list[str] = []
        timeline = ["Parsed issue", "Created bounded investigation plan"]
        tool_count = 0
        cycles = 0

        while cycles < max_retrieval_cycles:
            cycles += 1
            hits = self.retrieve(query, top_k=top_k)
            tool_count += 2  # hybrid retrieval + reranker
            for hit in hits:
                current = accumulated.get(hit.chunk_id)
                if current is None or hit.rerank_score > current.rerank_score:
                    accumulated[hit.chunk_id] = hit
            ranked = sorted(accumulated.values(), key=lambda item: item.rerank_score, reverse=True)[
                :top_k
            ]
            timeline.append(f"Retrieval cycle {cycles}: retained {len(ranked)} candidate symbols")

            _, nodes, new_evidence = self.graph_expand(ranked, graph_hops=graph_hops)
            tool_count += 1
            graph_nodes = list(dict.fromkeys([*graph_nodes, *nodes]))
            evidence.extend(new_evidence)
            timeline.append(f"Graph expansion cycle {cycles}: visited {len(nodes)} nodes")

            if self._evidence_sufficient(ranked, evidence, cycles, max_retrieval_cycles):
                timeline.append("Evidence sufficiency/stopping condition satisfied")
                break
            query = self._refine_query(request, identifiers, ranked, cycles + 1)
            timeline.append("Evidence insufficient; refined repository search query")

        ranked = sorted(accumulated.values(), key=lambda item: item.rerank_score, reverse=True)[
            :top_k
        ]
        timeline.append("Generated evidence-backed impact report")
        return self._report_from_hits(
            task_id=task_id,
            request=request,
            hits=ranked,
            evidence=evidence,
            graph_nodes=graph_nodes,
            timeline=timeline,
            retrieval_cycles=cycles,
            tool_count=tool_count,
        )


def build_langgraph(
    engine: InvestigationEngine, *, graph_hops: int = 2, top_k: int = 12, max_cycles: int = 3
):
    """Build an explicit bounded LangGraph investigation workflow.

    The graph exposes inspectable nodes and a conditional retrieval loop rather than
    wrapping the entire investigation inside one opaque node.
    """
    from langgraph.graph import END, StateGraph

    from repoatlas.agents.state import AgentState

    workflow = StateGraph(AgentState)

    def understand(state: AgentState):
        request = state["user_request"]
        return {
            "task_id": state.get("task_id") or str(uuid.uuid4()),
            "task_type": classify_task(request),
            "identifiers": extract_identifiers(request),
            "investigation_plan": plan(request),
            "search_queries": [request],
            "retrieval_cycles": 0,
            "tool_count": 0,
            "activity_timeline": ["Parsed issue", "Created bounded investigation plan"],
        }

    def retrieve_node(state: AgentState):
        query = state.get("search_queries", [state["user_request"]])[-1]
        hits = engine.retrieve(query, top_k=top_k)
        serialized = [item.model_dump() for item in hits]
        timeline = [
            *state.get("activity_timeline", []),
            f"Retrieved/reranked {len(hits)} candidate symbols",
        ]
        return {
            "retrieved_symbols": serialized,
            "candidate_symbols": [item.qualified_symbol for item in hits],
            "candidate_files": list(dict.fromkeys(item.file_path for item in hits)),
            "retrieval_cycles": state.get("retrieval_cycles", 0) + 1,
            "tool_count": state.get("tool_count", 0) + 2,
            "activity_timeline": timeline,
        }

    def graph_node(state: AgentState):
        from repoatlas.schemas.retrieval import RetrievedCode

        hits = [RetrievedCode.model_validate(item) for item in state.get("retrieved_symbols", [])]
        seeds, nodes, evidence = engine.graph_expand(hits, graph_hops=graph_hops)
        timeline = [
            *state.get("activity_timeline", []),
            f"Expanded {len(seeds)} graph seeds to {len(nodes)} nodes",
        ]
        return {
            "graph_seeds": seeds,
            "graph_evidence": evidence,
            "tool_count": state.get("tool_count", 0) + 1,
            "activity_timeline": timeline,
        }

    def route_after_graph(state: AgentState):
        cycles = state.get("retrieval_cycles", 1)
        hits = state.get("retrieved_symbols", [])
        evidence = state.get("graph_evidence", [])
        if engine._evidence_sufficient(hits, evidence, cycles, max_cycles):
            return "finalize"
        return "refine"

    def refine_node(state: AgentState):
        from repoatlas.schemas.retrieval import RetrievedCode

        hits = [RetrievedCode.model_validate(item) for item in state.get("retrieved_symbols", [])]
        query = engine._refine_query(
            state["user_request"],
            state.get("identifiers", []),
            hits,
            state.get("retrieval_cycles", 1) + 1,
        )
        return {
            "search_queries": [*state.get("search_queries", []), query],
            "activity_timeline": [
                *state.get("activity_timeline", []),
                "Evidence insufficient; refined search",
            ],
        }

    def finalize_node(state: AgentState):
        from repoatlas.schemas.retrieval import RetrievedCode

        hits = [RetrievedCode.model_validate(item) for item in state.get("retrieved_symbols", [])]
        graph_nodes = list(dict.fromkeys([*state.get("graph_seeds", [])]))
        for edge in state.get("graph_evidence", []):
            graph_nodes.extend([edge.get("source"), edge.get("target")])
        graph_nodes = [node for node in dict.fromkeys(graph_nodes) if node in engine.graph]
        timeline = [*state.get("activity_timeline", []), "Generated evidence-backed impact report"]
        report = engine._report_from_hits(
            task_id=state["task_id"],
            request=state["user_request"],
            hits=hits,
            evidence=state.get("graph_evidence", []),
            graph_nodes=graph_nodes,
            timeline=timeline,
            retrieval_cycles=state.get("retrieval_cycles", 1),
            tool_count=state.get("tool_count", 0),
        )
        return {"final_report": report, "activity_timeline": timeline}

    workflow.add_node("understand", understand)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("graph_expand", graph_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("finalize", finalize_node)
    workflow.set_entry_point("understand")
    workflow.add_edge("understand", "retrieve")
    workflow.add_edge("retrieve", "graph_expand")
    workflow.add_conditional_edges(
        "graph_expand",
        route_after_graph,
        {"refine": "refine", "finalize": "finalize"},
    )
    workflow.add_edge("refine", "retrieve")
    workflow.add_edge("finalize", END)
    return workflow.compile()
