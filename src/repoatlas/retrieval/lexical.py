import math
import re
from collections import Counter

from repoatlas.schemas.retrieval import RetrievedCode
from repoatlas.schemas.symbols import CodeChunk

TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\s]")


def tokenize(text: str) -> list[str]:
    return [x.lower() for x in TOKEN.findall(text)]


class BM25Index:
    def __init__(self, chunks: list[CodeChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.docs = [
            tokenize(c.qualified_symbol + " " + c.signature + " " + c.content) for c in chunks
        ]
        self.freq = [Counter(x) for x in self.docs]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        self.df = Counter()
        for d in self.freq:
            for t in d:
                self.df[t] += 1

    def score(self, q: str, i: int) -> float:
        s = 0.0
        n = len(self.docs)
        dl = len(self.docs[i])
        for t in tokenize(q):
            if t not in self.df:
                continue
            idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
            tf = self.freq[i][t]
            s += (
                idf
                * (tf * (self.k1 + 1))
                / (tf + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1)))
            )
        return s

    def search(self, q: str, top_k: int = 40) -> list[RetrievedCode]:
        scored = sorted(
            ((self.score(q, i), c) for i, c in enumerate(self.chunks)),
            key=lambda x: x[0],
            reverse=True,
        )[:top_k]
        return [
            RetrievedCode(
                chunk_id=c.chunk_id,
                file_path=c.file_path,
                qualified_symbol=c.qualified_symbol,
                content=c.content,
                lexical_score=float(s),
                evidence=[
                    f"[SYM: {c.qualified_symbol}]",
                    f"[SRC: {c.file_path}:L{c.start_line}-L{c.end_line}]",
                ],
            )
            for s, c in scored
            if s > 0
        ]
