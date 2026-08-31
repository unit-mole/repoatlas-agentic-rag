def filter_results(items, file_prefix: str | None = None, tests_only: bool = False):
    out = []
    for x in items:
        if file_prefix and not x.file_path.startswith(file_prefix):
            continue
        if tests_only and not (x.file_path.startswith("tests/") or "test_" in x.qualified_symbol):
            continue
        out.append(x)
    return out
