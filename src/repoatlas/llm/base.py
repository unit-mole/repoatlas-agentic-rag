from typing import Protocol


class ModelProvider(Protocol):
    def complete(
        self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 2048
    ) -> str: ...
