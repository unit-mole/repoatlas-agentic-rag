from pydantic import BaseModel, Field


class Symbol(BaseModel):
    repository_id: str
    commit_hash: str | None = None
    file_path: str
    name: str
    qualified_symbol: str
    symbol_type: str
    start_line: int
    end_line: int
    parent_symbol: str | None = None
    signature: str = ""
    docstring: str = ""
    content: str = ""
    imports: list[str] = Field(default_factory=list)
    test_flag: bool = False
    visibility: str = "public"
    content_hash: str = ""


class CodeChunk(Symbol):
    chunk_id: str
