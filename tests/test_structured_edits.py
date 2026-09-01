from repoatlas.patching.structured_edits import (
    StructuredEdit,
    apply_structured_edits,
    evidence_ranges,
    extract_structured_edits,
)


def test_evidence_ranges():
    evidence = "Source: src/demo.py:L10-L20\nSource: tests/test_demo.py:L5-L9\n"

    result = evidence_ranges(evidence)

    assert result == {
        "src/demo.py": [
            (
                10,
                20,
            )
        ],
        "tests/test_demo.py": [
            (
                5,
                9,
            )
        ],
    }


def test_extract_valid_line_edit():
    response = """\
{
  "edits": [
    {
      "file_path": "src/demo.py",
      "start_line": 2,
      "end_line": 2,
      "replacement": "    value = 2",
      "reason": "Update value"
    }
  ]
}
"""

    edits = extract_structured_edits(
        response,
        approved_files={"src/demo.py"},
        allowed_ranges={
            "src/demo.py": [
                (
                    1,
                    5,
                )
            ]
        },
    )

    assert len(edits) == 1

    assert edits[0].start_line == 2

    assert edits[0].end_line == 2


def test_rejects_range_outside_evidence():
    response = """\
{
  "edits": [
    {
      "file_path": "src/demo.py",
      "start_line": 20,
      "end_line": 21,
      "replacement": "value = 2"
    }
  ]
}
"""

    try:
        extract_structured_edits(
            response,
            approved_files={"src/demo.py"},
            allowed_ranges={
                "src/demo.py": [
                    (
                        1,
                        5,
                    )
                ]
            },
        )
    except ValueError as exc:
        assert "outside retrieved evidence" in str(exc)
    else:
        raise AssertionError("Expected evidence-range rejection.")


def test_apply_line_edit(
    tmp_path,
):
    workspace = tmp_path / "workspace"

    target = workspace / "src" / "demo.py"

    target.parent.mkdir(parents=True)

    target.write_text(
        ("class Demo:\n    value = 1\n    enabled = True\n"),
        encoding="utf-8",
    )

    result = apply_structured_edits(
        workspace=workspace,
        edits=[
            StructuredEdit(
                file_path="src/demo.py",
                start_line=2,
                end_line=2,
                replacement=("    value = 2"),
            )
        ],
        allowed_files=["src/demo.py"],
    )

    assert result["ok"] is True

    assert target.read_text(encoding="utf-8") == (
        "class Demo:\n    value = 2\n    enabled = True\n"
    )


def test_line_edits_are_transactional(
    tmp_path,
):
    workspace = tmp_path / "workspace"

    first = workspace / "src" / "one.py"

    second = workspace / "src" / "two.py"

    first.parent.mkdir(parents=True)

    first.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    second.write_text(
        "other = 1\n",
        encoding="utf-8",
    )

    result = apply_structured_edits(
        workspace=workspace,
        edits=[
            StructuredEdit(
                file_path="src/one.py",
                start_line=1,
                end_line=1,
                replacement="value = 2",
            ),
            StructuredEdit(
                file_path="src/two.py",
                start_line=99,
                end_line=99,
                replacement="other = 2",
            ),
        ],
        allowed_files=[
            "src/one.py",
            "src/two.py",
        ],
    )

    assert result["ok"] is False

    assert first.read_text(encoding="utf-8") == "value = 1\n"

    assert second.read_text(encoding="utf-8") == "other = 1\n"
