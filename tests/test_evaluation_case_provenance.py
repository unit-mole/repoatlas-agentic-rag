from repoatlas.schemas.evaluation import EvaluationCase


def test_evaluation_case_preserves_file_provenance():
    case = EvaluationCase(
        case_id="demo-case",
        repository="demo",
        base_commit="base123",
        fix_commit="fix456",
        issue_text="Demo historical change.",
        all_changed_files=[
            "src/example.py",
            "README.md",
        ],
        expected_changed_files=[
            "src/example.py",
        ],
        excluded_changed_files=[
            "README.md",
        ],
        expected_changed_symbols=[
            "src/example.py::run",
        ],
        expected_tests=[],
    )

    dumped = case.model_dump()

    assert dumped["all_changed_files"] == [
        "src/example.py",
        "README.md",
    ]

    assert dumped["expected_changed_files"] == [
        "src/example.py",
    ]

    assert dumped["excluded_changed_files"] == [
        "README.md",
    ]

    assert set(case.expected_changed_files) | set(case.excluded_changed_files) == set(
        case.all_changed_files
    )
