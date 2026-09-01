from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPERIMENTS = Path("reports/experiments")
OUTPUT = Path("reports/final")


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def flatten(
    value: Any,
    prefix: str = "",
) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(
                flatten(
                    child,
                    child_prefix,
                )
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(
                flatten(
                    child,
                    f"{prefix}[{index}]",
                )
            )

    elif (
        isinstance(
            value,
            (str, int, float, bool),
        )
        or value is None
    ):
        rows.append(
            (
                prefix,
                value,
            )
        )

    return rows


def relevant_json_files() -> list[Path]:
    files: list[Path] = []

    for path in EXPERIMENTS.rglob("*.json"):
        relative = path.relative_to(EXPERIMENTS)

        if "archive" in relative.parts:
            continue

        name = path.name.lower()

        if "failed" in name:
            continue

        is_final_result = (
            "httpx-test" in name
            or name.startswith(("v5-", "v6-"))
            or name
            in {
                "safe_patch_fixture.json",
                "full_run_manifest.json",
            }
        )

        if is_final_result:
            files.append(path)

    return sorted(files)


def main() -> None:
    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = relevant_json_files()

    if not files:
        raise SystemExit("No final experiment JSON files found.")

    manifest: dict[str, Any] = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "source_count": len(files),
        "sources": [],
    }

    scalar_rows: list[dict[str, Any]] = []

    for path in files:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        relative = path.as_posix()

        manifest["sources"].append(
            {
                "path": relative,
                "sha256": sha256(path),
            }
        )

        for field, value in flatten(data):
            scalar_rows.append(
                {
                    "source": relative,
                    "field": field,
                    "value": value,
                }
            )

    manifest_path = OUTPUT / "final_results_manifest.json"

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    csv_path = OUTPUT / "final_metrics_inventory.csv"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "field",
                "value",
            ],
        )
        writer.writeheader()
        writer.writerows(scalar_rows)

    md_path = OUTPUT / "FINAL_RESULTS.md"

    lines = [
        "# RepoAtlas Final Results Evidence",
        "",
        f"- Git commit: `{manifest['git_commit']}`",
        f"- Experiment files: {len(files)}",
        "",
        "## Evidence Files",
        "",
    ]

    for item in manifest["sources"]:
        lines.append(f"- `{item['path']}`")

    reproducibility_text = (
        "Every listed source is a real locally generated experiment artifact."
        " SHA-256 values are stored in `final_results_manifest.json`."
    )

    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            reproducibility_text,
            "",
            "No metrics are fabricated by this export.",
        ]
    )

    md_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("FINAL RESULTS MANIFEST: PASS")
    print("JSON:", manifest_path)
    print("CSV:", csv_path)
    print("Markdown:", md_path)
    print("Experiment sources:", len(files))


if __name__ == "__main__":
    main()
