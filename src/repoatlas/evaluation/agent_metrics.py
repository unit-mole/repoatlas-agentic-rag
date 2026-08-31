def agent_metrics(rows: list[dict]):
    if not rows:
        return {"task_completion": 0.0, "avg_steps": 0.0, "agent_loop_rate": 0.0}
    return {
        "task_completion": sum(bool(x.get("completed")) for x in rows) / len(rows),
        "avg_steps": sum(x.get("steps", 0) for x in rows) / len(rows),
        "agent_loop_rate": sum(bool(x.get("loop")) for x in rows) / len(rows),
    }
