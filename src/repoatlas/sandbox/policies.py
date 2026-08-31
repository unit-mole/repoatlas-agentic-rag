from pydantic import BaseModel, Field


class SandboxPolicy(BaseModel):
    image: str = "repoatlas-sandbox:latest"
    network: str = "none"
    cpus: float = Field(default=2.0, gt=0, le=8)
    memory: str = "4g"
    pids_limit: int = Field(default=128, ge=16, le=512)
    timeout_seconds: int = Field(default=180, ge=5, le=1800)
    read_only_root: bool = True
    drop_capabilities: bool = True
    tmpfs_size: str = "128m"
    output_limit_chars: int = Field(default=50_000, ge=1_000, le=500_000)
