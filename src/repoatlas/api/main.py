from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from repoatlas.pipeline import build_runtime

app = FastAPI(title="RepoAtlas API", version="0.1.0")
RUNTIMES = {}
TASKS = {}


class IndexRequest(BaseModel):
    repository_id: str
    path: str
    embedding: str = "hash"
    reranker: str = "heuristic"


class TaskRequest(BaseModel):
    repository_id: str
    request: str
    graph_hops: int = 2


@app.get("/health")
def health():
    return {"status": "ok", "write_mode": False}


@app.get("/repositories")
def repositories():
    return {"repositories": list(RUNTIMES)}


@app.post("/repositories/index")
def index(req: IndexRequest):
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(404, "repository path not found")
    rt = build_runtime(p, req.embedding, req.reranker)
    RUNTIMES[req.repository_id] = rt
    return {
        "repository_id": req.repository_id,
        "symbols": len(rt["symbols"]),
        "chunks": len(rt["chunks"]),
        "graph_nodes": rt["graph"].number_of_nodes(),
        "graph_edges": rt["graph"].number_of_edges(),
    }


@app.post("/tasks/investigate")
def investigate(req: TaskRequest):
    if req.repository_id not in RUNTIMES:
        raise HTTPException(404, "repository not indexed")
    report = RUNTIMES[req.repository_id]["engine"].investigate(req.request, req.graph_hops)
    TASKS[report["task_id"]] = report
    return report


@app.get("/tasks/{task_id}")
def task(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, "task not found")
    return TASKS[task_id]


@app.post("/retrieval/debug")
def retrieval_debug(req: TaskRequest):
    if req.repository_id not in RUNTIMES:
        raise HTTPException(404, "repository not indexed")
    return {
        "items": [x.model_dump() for x in RUNTIMES[req.repository_id]["hybrid"].search(req.request)]
    }


@app.get("/metrics/summary")
def metrics_summary():
    return {"status": "TBD until evaluation run", "reports_path": "reports/experiments"}


@app.post("/tasks/{task_id}/approve")
def approve(task_id: str):
    return {"task_id": task_id, "status": "accepted_for_local_export_only", "remote_action": False}


@app.post("/tasks/{task_id}/reject")
def reject(task_id: str):
    return {"task_id": task_id, "status": "rejected"}
