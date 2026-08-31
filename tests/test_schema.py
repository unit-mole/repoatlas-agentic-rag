import pytest

from repoatlas.schemas.evaluation import EvaluationCase


def test_reject_same_fix_base():
    with pytest.raises(ValueError):
        EvaluationCase(case_id="x", repository="r", base_commit="a", fix_commit="a", issue_text="x")
