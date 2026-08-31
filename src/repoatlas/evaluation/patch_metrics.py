def patch_metrics(rows: list[dict]):
    if not rows:
        return {
            "task_success": 0.0,
            "target_test_pass_rate": 0.0,
            "unrelated_file_modification_rate": 0.0,
        }
    n = len(rows)
    return {
        "task_success": sum(bool(x.get("success")) for x in rows) / n,
        "target_test_pass_rate": sum(bool(x.get("target_tests_pass")) for x in rows) / n,
        "unrelated_file_modification_rate": sum(bool(x.get("unrelated_change")) for x in rows) / n,
    }
