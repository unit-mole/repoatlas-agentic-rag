from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from repoatlas.patching.application import apply_unified_patch, workspace_diff
from repoatlas.patching.verifier import verify_diff
from repoatlas.sandbox.manager import SandboxManager, create_workspace

PATCH = """diff --git a/src/demo/cache.py b/src/demo/cache.py
--- a/src/demo/cache.py
+++ b/src/demo/cache.py
@@ -1,4 +1,4 @@
 class Cache:
-    def __init__(self, timeout=30): self.timeout=timeout; self.values={}
+    def __init__(self, timeout=60): self.timeout=timeout; self.values={}
     def get(self,key): return self.values.get(key)
     def set(self,key,value): self.values[key]=value
"""


def local_tests(workspace: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "mode": "local-build-validation",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/fixture_repo")
    parser.add_argument("--workspace", default="workspaces/fixture-safe-patch")
    parser.add_argument(
        "--docker", action="store_true", help="Run pytest in the restricted Docker sandbox."
    )
    args = parser.parse_args()

    source = Path(args.source)
    workspace = create_workspace(source, Path(args.workspace))
    applied = apply_unified_patch(workspace, PATCH)
    if not applied["ok"]:
        print(json.dumps({"applied": applied}, indent=2))
        raise SystemExit(1)

    tests = SandboxManager().run_pytest(workspace, []) if args.docker else local_tests(workspace)
    diff = workspace_diff(workspace)
    verification = verify_diff(diff, tests)

    original = (source / "src/demo/cache.py").read_text(encoding="utf-8")
    original_unchanged = "timeout=30" in original and "timeout=60" not in original

    result = {
        "applied": applied,
        "tests": tests,
        "diff": diff,
        "verification": verification.model_dump(),
        "original_unchanged": original_unchanged,
        "workspace": str(workspace),
    }
    out = Path("reports/experiments/safe_patch_fixture.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if verification.passed and original_unchanged else 1)


if __name__ == "__main__":
    main()
