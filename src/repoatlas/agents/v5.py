from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from repoatlas.graph.protected_augmentation import (
    protected_graph_augmentation,
)
from repoatlas.graph.test_discovery import (
    discover_related_tests,
)


SYSTEM_PROMPT = """\
You are RepoAtlas V5, an evidence-grounded software engineering
investigation agent.

You are given evidence retrieved from a frozen repository snapshot.

Rules:
1. Use only the supplied repository evidence.
2. Do not claim that a file, symbol, dependency, test, or behavior exists
   unless the evidence supports it.
3. Every concrete repository claim must cite at least one evidence ID,
   such as [D1], [G2], or [T1].
4. Distinguish observed evidence from engineering inference.
5. If evidence is insufficient, explicitly say so.
6. Do not produce a patch.
7. Do not invent test results.
8. Keep the response concise and useful to a software engineer.

Return sections:
- Issue understanding
- Likely change locations
- Repository evidence
- Suggested verification
- Risks / uncertainty
- Recommended next action
"""


def _safe_float(value: Any) -> float:
    try:
        return round(
            float(value),
            6,
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _trim(value: Any, limit: int = 1400) -> str:
    text = str(value or "").strip()

    if len(text) <= limit:
        return text

    return text[:limit] + "...[truncated]"


class V5InvestigationAgent:
    """Frozen-retrieval investigation agent with local LLM synthesis.

    Runtime ranking remains deterministic:

    V2 hybrid retrieval
        -> V4P protected graph augmentation
        -> V2 reverse-TESTS discovery
        -> local LLM evidence synthesis

    The LLM is not allowed to alter retrieval ranking.
    """

    def __init__(
        self,
        *,
        repo: Path,
        runtime: dict[str, Any],
        provider: Any,
    ) -> None:
        self.repo = repo.resolve()
        self.runtime = runtime
        self.provider = provider

    def _base_commit(self) -> str | None:
        marker = (
            self.repo
            / ".repoatlas_base_commit"
        )

        if not marker.exists():
            return None

        return marker.read_text(
            encoding="utf-8"
        ).strip()

    def investigate(
        self,
        task: str,
        *,
        direct_limit: int = 30,
        graph_limit: int = 10,
        test_limit: int = 20,
    ) -> dict[str, Any]:
        task_id = str(
            uuid.uuid4()
        )

        direct_hits = list(
            self.runtime[
                "hybrid"
            ].search(task)
        )[:direct_limit]

        if not direct_hits:
            raise RuntimeError(
                "V2 returned no repository evidence."
            )

        protected = protected_graph_augmentation(
            direct_hits=direct_hits,
            graph=self.runtime["graph"],
            max_hops=1,
            seed_limit=5,
            max_added_nodes=25,
            protected_symbol_k=10,
            protected_file_k=10,
        )

        discovered_tests = discover_related_tests(
            self.runtime["graph"],
            direct_hits,
            limit=test_limit,
        )

        direct_evidence = []

        for index, hit in enumerate(
            direct_hits[:12],
            start=1,
        ):
            direct_evidence.append(
                {
                    "id": f"D{index}",
                    "file": hit.file_path,
                    "symbol": hit.qualified_symbol,
                    "fusion_score": _safe_float(
                        getattr(
                            hit,
                            "fusion_score",
                            0.0,
                        )
                    ),
                    "evidence": _trim(
                        getattr(
                            hit,
                            "evidence",
                            "",
                        )
                    ),
                }
            )

        graph_evidence = []

        for index, item in enumerate(
            protected.graph_candidates[
                :graph_limit
            ],
            start=1,
        ):
            graph_evidence.append(
                {
                    "id": f"G{index}",
                    **item,
                }
            )

        test_evidence = []

        for index, candidate in enumerate(
            discovered_tests,
            start=1,
        ):
            test_evidence.append(
                {
                    "id": f"T{index}",
                    "file": candidate.file_path,
                    "best_source_rank": (
                        candidate.best_source_rank
                    ),
                    "supporting_sources": (
                        candidate.supporting_sources
                    ),
                    "supporting_edges": (
                        candidate.supporting_edges
                    ),
                    "evidence": (
                        candidate.evidence[:5]
                    ),
                }
            )

        evidence_bundle = {
            "task": task,
            "repository": self.repo.name,
            "base_commit": self._base_commit(),
            "direct_v2_evidence": direct_evidence,
            "graph_evidence": graph_evidence,
            "related_test_evidence": (
                test_evidence
            ),
        }

        user_prompt = (
            "Investigate the following software "
            "engineering issue using only the "
            "evidence bundle.\n\n"
            + json.dumps(
                evidence_bundle,
                indent=2,
            )
        )

        synthesis = self.provider.complete(
            SYSTEM_PROMPT,
            user_prompt,
            temperature=0.1,
            max_tokens=1200,
        )

        return {
            "task_id": task_id,
            "agent_version": "V5",
            "mode": (
                "frozen_retrieval_local_llm"
            ),
            "task": task,
            "repository": str(
                self.repo
            ),
            "base_commit": (
                self._base_commit()
            ),
            "retrieval": {
                "primary": (
                    "V2_BM25_BGE_M3_RRF"
                ),
                "graph": (
                    "V4P_PROTECTED_CONTEXT"
                ),
                "test_discovery": (
                    "V2_REVERSE_TESTS"
                ),
                "v3s_default": False,
                "direct_hits": len(
                    direct_hits
                ),
                "protected_prefix_size": (
                    protected.protected_prefix_size
                ),
                "graph_candidates": len(
                    protected.graph_candidates
                ),
                "related_tests": len(
                    discovered_tests
                ),
            },
            "likely_affected_files": (
                protected.files[:15]
            ),
            "likely_primary_symbols": (
                protected.symbols[:20]
            ),
            "related_tests": [
                item.file_path
                for item in discovered_tests[
                    :10
                ]
            ],
            "evidence": {
                "direct": direct_evidence,
                "graph": graph_evidence,
                "tests": test_evidence,
            },
            "llm": {
                "provider": (
                    self.provider.__class__.__name__
                ),
                "role": (
                    "evidence synthesis only"
                ),
            },
            "investigation_report": (
                synthesis
            ),
        }
