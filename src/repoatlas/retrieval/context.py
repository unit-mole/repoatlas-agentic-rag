from pathlib import Path

from repoatlas.security.path_validation import safe_resolve


def expand_source_context(
    repo_root: Path, file_path: str, start: int, end: int, padding: int = 12
) -> str:
    p = safe_resolve(repo_root, file_path, True)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    a = max(start - padding, 1)
    b = min(end + padding, len(lines))
    return "\n".join(f"{i + 1:5d} {lines[i]}" for i in range(a - 1, b))
