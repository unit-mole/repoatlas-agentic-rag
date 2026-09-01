# Data Sources

Default demo target: `https://github.com/encode/httpx.git` (BSD-3-Clause project). RepoAtlas stores clones/snapshots under ignored `data/repositories/` and `data/snapshots/` paths.

Benchmark cases must use public repositories, public issue/PR metadata, synthetic tasks, or benchmark repositories whose licenses permit use. Never add employer-confidential source code.

Historical evaluation rule: checkout the **base commit before the fix**, cut Git history at that commit, and keep gold patches/changed files/symbols outside the agent-visible index.
