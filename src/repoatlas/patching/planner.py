from repoatlas.schemas.patches import PatchFilePlan, PatchProposal


def deterministic_patch_plan(task_id, task, candidates):
    files = []
    seen = set()
    for c in candidates[:5]:
        if c.file_path in seen:
            continue
        seen.add(c.file_path)
        files.append(
            PatchFilePlan(
                file_path=c.file_path,
                reason="High impact-relevance evidence for requested change",
                symbols=[c.qualified_symbol],
                intended_modification="Inspect and make the smallest behavior-preserving change required by the task.",
            )
        )
    return PatchProposal(task_id=task_id, summary=task, files=files)
