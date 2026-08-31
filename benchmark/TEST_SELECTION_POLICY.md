# RepoAtlas Historical TEST Selection Policy

## Purpose

TEST measures generalization of the retrieval architecture frozen at:

- Git tag: retrieval-dev-freeze-v1
- Frozen configuration: configs/retrieval_frozen_v1.json
- Configuration SHA-256:
  57e20457c7728d3886f6914f63d4f4aef711cd85b262e24606ca09199a2a14b6

TEST results must not be used to tune the frozen retrieval architecture.

## Selection rules

Historical TEST cases must:

1. Come from the HTTPX Git history.
2. Be distinct from every DEV FIX and DEV BASE commit.
3. Represent a real historical code change.
4. Have a single pre-fix parent commit that can serve as BASE.
5. Change at least one Python source file.
6. Change at least one Python test file.
7. Avoid release-only, documentation-only, version-only, and formatting-only changes.
8. Prefer reasonably bounded changes suitable for localization evaluation.
9. Prefer diversity across software-engineering failure categories.
10. Be selected without running RepoAtlas retrieval against the candidate.

## Leakage policy

During runtime evaluation:

- only the frozen BASE repository is available;
- the FIX commit is not available;
- future commits are not available;
- the gold patch is evaluator-only;
- expected changed files/symbols/tests are evaluator-only.

## Tuning policy

The following are frozen before TEST:

- V2 lexical_k = 40
- V2 dense_k = 40
- V2 fusion_k = 30

V4P:

- max_hops = 1
- seed_limit = 5
- max_added_nodes = 25
- protected_symbol_k = 10
- protected_file_k = 10

V3S:

- file_limit = 5
- candidate_limit = 12

TEST metrics will be reported as observed.

No parameter may be changed because of TEST performance.
