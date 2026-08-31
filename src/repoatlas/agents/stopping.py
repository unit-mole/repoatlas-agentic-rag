def should_stop(state, limits):
    return (
        state.get("tool_count", 0) >= limits.tool_calls
        or state.get("retrieval_cycles", 0) >= limits.retrieval_cycles
        or state.get("approval_state") == "required"
    )
