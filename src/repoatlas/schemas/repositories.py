from pathlib import Path

from pydantic import BaseModel


class Repository(BaseModel):
    repository_id: str
    name: str
    url: str | None = None
    local_path: Path
    commit_hash: str | None = None
    language: str = "python"
    license: str | None = None


class SourceFile(BaseModel):
    repository_id: str
    path: str
    language: str
    size_bytes: int
    sha256: str
