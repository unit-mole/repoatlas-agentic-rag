from pydantic import BaseModel, Field, model_validator


class EvaluationCase(BaseModel):
    case_id: str
    repository: str
    base_commit: str
    issue_text: str

    # Complete Git provenance from the historical fix. This can include
    # documentation, metadata, and other files outside the current
    # symbol-level retrieval corpus.
    all_changed_files: list[str] = Field(default_factory=list)

    # Fair retrieval gold. These are historical changed files that are
    # structurally retrievable from the frozen pre-fix RepoAtlas corpus.
    expected_changed_files: list[str] = Field(default_factory=list)

    # Historical changed files deliberately excluded from retrieval
    # metrics because the current retrieval corpus cannot return them.
    excluded_changed_files: list[str] = Field(default_factory=list)

    expected_changed_symbols: list[str] = Field(default_factory=list)
    expected_tests: list[str] = Field(default_factory=list)
    gold_patch: str | None = None
    fix_commit: str | None = None
    difficulty: str = "medium"
    category: str = "bug_localization"
    split: str = "dev"

    @model_validator(mode="after")
    def validate_split(self):
        if self.split not in {"dev", "test"}:
            raise ValueError("split must be dev or test")
        if self.fix_commit and self.fix_commit == self.base_commit:
            raise ValueError("fix_commit must differ from base_commit")

        if self.all_changed_files:
            all_files = set(self.all_changed_files)
            retrieval_files = set(self.expected_changed_files)
            excluded_files = set(self.excluded_changed_files)

            if retrieval_files & excluded_files:
                raise ValueError(
                    "expected_changed_files and excluded_changed_files must be disjoint"
                )

            if retrieval_files | excluded_files != all_files:
                raise ValueError(
                    "expected_changed_files + excluded_changed_files "
                    "must partition all_changed_files"
                )

            if not set(self.expected_tests).issubset(retrieval_files):
                raise ValueError("expected_tests must be retrieval-localizable files")
        return self


class ExperimentRecord(BaseModel):
    experiment_id: str
    timestamp: str
    git_commit: str | None = None
    repo_snapshot: str
    benchmark_version: str
    model: str
    embedding: str
    reranker: str
    lexical_config: dict = Field(default_factory=dict)
    fusion_config: dict = Field(default_factory=dict)
    graph_hops: int = 0
    graph_limits: dict = Field(default_factory=dict)
    top_k: int = 10
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    latency: dict[str, float] = Field(default_factory=dict)
    vram: dict[str, float | str] = Field(default_factory=dict)
    notes: str = ""
