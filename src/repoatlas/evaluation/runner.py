import csv
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from repoatlas.evaluation.retrieval_metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k


def evaluate_cases(cases, run_case, version="V0", out_dir=Path("reports/experiments")):
    rows = []
    for c in cases:
        t = time.perf_counter()
        result = run_case(c)
        latency = time.perf_counter() - t
        pf = result.get("files", [])
        ps = result.get("symbols", [])
        row = {
            "case_id": c.case_id,
            "version": version,
            "file_r5": recall_at_k(pf, c.expected_changed_files, 5),
            "file_r10": recall_at_k(pf, c.expected_changed_files, 10),
            "symbol_r5": recall_at_k(ps, c.expected_changed_symbols, 5),
            "symbol_r10": recall_at_k(ps, c.expected_changed_symbols, 10),
            "precision10": precision_at_k(pf, c.expected_changed_files, 10),
            "mrr": mrr(pf, c.expected_changed_files),
            "ndcg10": ndcg_at_k(pf, c.expected_changed_files, 10),
            "latency_s": latency,
        }
        rows.append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    eid = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + version + "-" + uuid.uuid4().hex[:6]
    (out_dir / f"{eid}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if rows:
        with (out_dir / f"{eid}.csv").open("w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=rows[0].keys())
            wr.writeheader()
            wr.writerows(rows)
        md = (
            "|"
            + "|".join(rows[0].keys())
            + "|\n|"
            + "|".join(["---"] * len(rows[0]))
            + "|\n"
            + "".join("|" + "|".join(str(r[k]) for k in rows[0]) + "|\n" for r in rows)
        )
        (out_dir / f"{eid}.md").write_text(md, encoding="utf-8")
    return rows
