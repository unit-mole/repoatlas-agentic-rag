from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    tool: str
    ok: bool
    data: dict = Field(default_factory=dict)
    message: str = ""
    duration_ms: float = 0.0
