from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    model_provider: str = "local"
    local_llm_base_url: str = "http://localhost:8000/v1"
    local_llm_model: str = "Qwen/Qwen3-8B"
    primary_benchmark_model: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    qdrant_mode: str = "local"
    qdrant_url: str = "http://localhost:6333"
    database_url: str = "sqlite:///data/repoatlas.db"
    phoenix_endpoint: str = "http://localhost:6006/v1/traces"
    repo_root: Path = Path("data/repositories")
    sandbox_image: str = "repoatlas-sandbox:latest"
    sandbox_network: bool = False
    enable_mcp: bool = True
    enable_write_tools: bool = False
    enable_commercial_models: bool = False
    max_tool_calls: int = 20
    max_retrieval_cycles: int = 3
    max_patch_attempts: int = 2


def get_settings() -> Settings:
    return Settings()
