import argparse
from pathlib import Path

from repoatlas.repositories.snapshots import create_snapshot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="data/repositories/httpx")
    ap.add_argument("--dest", default="data/snapshots/httpx")
    ap.add_argument("--base-commit", default="HEAD")
    a = ap.parse_args()
    print(create_snapshot(Path(a.repo), Path(a.dest), a.base_commit))


if __name__ == "__main__":
    main()
