from pydantic import BaseModel


class GraphNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    file_path: str | None = None
    symbol: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    file: str | None = None
    line: int | None = None
    confidence: float = 1.0
    extraction_method: str = "static"
