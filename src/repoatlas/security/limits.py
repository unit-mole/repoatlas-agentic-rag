from dataclasses import dataclass


@dataclass
class AgentLimits:
    retrieval_cycles: int = 3
    patch_attempts: int = 2
    tool_calls: int = 20
    test_retries: int = 2
