from repoatlas.agents.planner import classify_task, extract_identifiers, plan


def understand(state):
    t = state["user_request"]
    return {
        "task_type": classify_task(t),
        "identifiers": extract_identifiers(t),
        "investigation_plan": plan(t),
    }
