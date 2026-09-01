from repoatlas.patching.generator import (
    extract_unified_diff,
)


def test_extract_unified_diff_recounts_bad_hunk_counts():
    model_output = (
        "diff --git a/src/demo.py b/src/demo.py\n"
        "--- a/src/demo.py\n"
        "+++ b/src/demo.py\n"
        "@@ -1,99 +1,88 @@\n"
        " class Demo:\n"
        "-    value = 1\n"
        "+    value = 2\n"
    )

    patch = extract_unified_diff(model_output)

    assert "@@ -1,2 +1,2 @@" in patch

    assert "-    value = 1" in patch

    assert "+    value = 2" in patch


def test_extract_unified_diff_normalizes_internal_empty_context_line():
    model_output = (
        "diff --git a/src/demo.py b/src/demo.py\n"
        "--- a/src/demo.py\n"
        "+++ b/src/demo.py\n"
        "@@ -1,20 +1,20 @@\n"
        " def demo():\n"
        "-    return 1\n"
        "+    return 2\n"
        "\n"
        " def other():\n"
        "     return 3\n"
    )

    patch = extract_unified_diff(model_output)

    assert "@@ -1,5 +1,5 @@" in patch

    assert "\n \n" in patch
