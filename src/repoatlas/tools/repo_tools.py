from pathlib import Path

from repoatlas.security.path_validation import safe_resolve


class RepositoryTools:
    def __init__(self, repo_root: Path, retriever=None):
        self.root = repo_root
        self.retriever = retriever

    def search_repository(self, query: str, top_k: int = 10):
        return self.retriever.search(query, fusion_k=top_k) if self.retriever else []

    def search_exact_text(self, text: str, limit: int = 50):
        hits = []
        for p in self.root.rglob("*.py"):
            try:
                for i, line in enumerate(
                    p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if text in line:
                        hits.append(
                            {
                                "file": p.relative_to(self.root).as_posix(),
                                "line": i,
                                "text": line.strip(),
                            }
                        )
                    if len(hits) >= limit:
                        return hits
            except OSError:
                pass
        return hits

    def read_file(self, path: str, max_chars: int = 100_000):
        return safe_resolve(self.root, path, True).read_text(encoding="utf-8", errors="replace")[
            :max_chars
        ]

    def list_directory(self, path: str = "."):
        return sorted(x.name for x in safe_resolve(self.root, path, True).iterdir())
