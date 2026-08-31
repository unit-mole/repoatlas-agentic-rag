from pydantic import BaseModel, Field


class PatchFilePlan(BaseModel):
    file_path: str
    reason: str
    symbols: list[str] = Field(default_factory=list)
    intended_modification: str


class PatchProposal(BaseModel):
    task_id: str
    summary: str
    files: list[PatchFilePlan] = Field(default_factory=list)
    unified_diff: str = ""


class VerificationResult(BaseModel):
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
