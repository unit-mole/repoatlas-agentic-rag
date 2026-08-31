import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(mod):
    p = subprocess.run([sys.executable, "-m", mod], text=True, capture_output=True, check=False)
    return {"module": mod, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", action="store_true")
    ap.parse_args()
    mods = [
        "scripts.create_fixture_repo",
        "scripts.build_benchmark",
        "scripts.validate_benchmark",
        "scripts.evaluate_retrieval",
        "scripts.evaluate_graph",
        "scripts.evaluate_agent",
        "scripts.safe_patch_fixture",
        "scripts.compile_ablation",
    ]
    rows = [run(m) for m in mods]
    out = Path("reports/experiments/full_run_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))
    raise SystemExit(1 if any(r["returncode"] for r in rows) else 0)


if __name__ == "__main__":
    main()
