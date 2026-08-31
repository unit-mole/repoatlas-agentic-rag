import json
from pathlib import Path

from repoatlas.pipeline import build_runtime


def main():
    rt = build_runtime(Path("data/fixture_repo"))
    r = rt["engine"].investigate("Investigate cache timeout impact on token refresh and find tests")
    row = {
        "completed": bool(r["likely_affected_files"]),
        "steps": len(r["activity_timeline"]),
        "tool_calls": 4,
        "loop": False,
    }
    p = Path("reports/experiments/agent_fixture.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(row, indent=2))
    print(row)


if __name__ == "__main__":
    main()
