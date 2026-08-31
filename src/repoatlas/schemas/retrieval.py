from pydantic import BaseModel, Field


class RetrievedCode(BaseModel):
    chunk_id: str
    file_path: str
    qualified_symbol: str
    content: str
    lexical_score: float = 0.0
    dense_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    graph_score: float = 0.0
    impact_relevance_score: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    query: str
    items: list[RetrievedCode]
