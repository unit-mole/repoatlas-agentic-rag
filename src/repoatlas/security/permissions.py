from dataclasses import dataclass

from repoatlas.core.constants import PermissionLevel


@dataclass(frozen=True)
class ToolPolicy:
    name: str
    level: PermissionLevel
    timeout_seconds: int = 30
    output_limit: int = 100_000


def authorize(policy: ToolPolicy, max_level: PermissionLevel) -> None:
    if policy.level > max_level:
        raise PermissionError(
            f"{policy.name} requires {policy.level.name}, allowed={max_level.name}"
        )
