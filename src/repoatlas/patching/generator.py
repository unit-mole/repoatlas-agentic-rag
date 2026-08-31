from __future__ import annotations

import re

from repoatlas.llm.prompts import PATCH, SYSTEM

_DIFF_START = re.compile(r"(?m)^diff --git ")


def extract_unified_diff(text: str) -> str:
    """Strip prose/markdown and return only a Git-style unified diff."""
    match = _DIFF_START.search(text)
    if not match:
        raise ValueError("Model response did not contain a Git-style unified diff.")
    diff = text[match.start() :].strip()
    if "```" in diff:
        diff = diff.split("```", 1)[0].rstrip()
    return diff + "\n"


def generate_patch(provider, task, plan, evidence):
    response = provider.complete(
        SYSTEM,
        PATCH.format(task=task, plan=plan.model_dump_json(indent=2), evidence=evidence),
        temperature=0.1,
        max_tokens=4096,
    )
    return extract_unified_diff(response)
