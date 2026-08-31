from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...
