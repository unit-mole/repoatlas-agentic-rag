# Benchmark Design

Each `EvaluationCase` contains `case_id`, repository, base commit, issue text, expected changed files, expected changed symbols, expected tests, gold patch/fix commit reference, difficulty, category, and split.

Leakage prevention is enforced by `BenchmarkValidator`: the agent repository is frozen at `base_commit`; future commits and gold patch text are excluded from retrieval. DEV is tunable; TEST is frozen.

Run `python -m scripts.build_benchmark` followed by `python -m scripts.run_full_evaluation`. Real metrics are written under `reports/experiments/`.
