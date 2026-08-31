from hashlib import sha256
from pathlib import Path

from repoatlas.core.constants import DEFAULT_IGNORES, MAX_FILE_BYTES
from repoatlas.repositories.languages import detect_language
from repoatlas.schemas.repositories import SourceFile


def scan_repository(repo_id: str, root: Path, language: str = "python") -> list[SourceFile]:
    out = []
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file() or any(part in DEFAULT_IGNORES for part in p.parts):
            continue
        lang = detect_language(p)
        if lang != language:
            continue
        size = p.stat().st_size
        if size > MAX_FILE_BYTES:
            continue
        data = p.read_bytes()
        if b"\x00" in data[:4096]:
            continue
        out.append(
            SourceFile(
                repository_id=repo_id,
                path=p.relative_to(root).as_posix(),
                language=lang,
                size_bytes=size,
                sha256=sha256(data).hexdigest(),
            )
        )
    return sorted(out, key=lambda x: x.path)
