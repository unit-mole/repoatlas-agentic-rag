import pytest

from repoatlas.schemas.evaluation import EvaluationCase


def test_rejects_overlapping_file_provenance():
    with pytest.raises(
        ValueError,
        match="must be disjoint",
    ):
        EvaluationCase(
            case_id="bad-case",
            repository="demo",
            base_commit="base123",
            fix_commit="fix456",
            issue_text="Demo.",
            all_changed_files=[
                "src/example.py",
            ],
            expected_changed_files=[
                "src/example.py",
            ],
            excluded_changed_files=[
                "src/example.py",
            ],
        )


def test_rejects_incomplete_file_partition():
    with pytest.raises(
        ValueError,
        match="must partition",
    ):
        EvaluationCase(
            case_id="bad-case",
            repository="demo",
            base_commit="base123",
            fix_commit="fix456",
            issue_text="Demo.",
            all_changed_files=[
                "src/example.py",
                "README.md",
            ],
            expected_changed_files=[
                "src/example.py",
            ],
            excluded_changed_files=[],
        )
