# RepoAtlas — Complete Local Execution Runbook

This is the execution order, not a staged delivery roadmap. The full codebase is already present.

## 1. PowerShell — verify Windows / WSL2 / GPU

```powershell
wsl --status
wsl --version
nvidia-smi
```

Success: WSL2 is enabled; `nvidia-smi` shows the RTX 5090 and driver. Send back the complete command output if WSL or GPU is missing.

## 2. WSL2 — clone/copy RepoAtlas to the Linux filesystem

Recommended path (faster than `/mnt/c` for heavy repo/index workloads):

```bash
mkdir -p ~/projects
cd ~/projects
# copy/unzip repoatlas here, then:
cd repoatlas
```

## 3. WSL2 — Python 3.12 environment

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install -e '.[dev]'
```

Success: editable install completes. Large model weights are not downloaded by this step.

## 4. WSL2 — environment report

```bash
python -m scripts.environment_report | tee reports/environment_report.json
```

Send this file/output back after the first run.

## 5. Docker Desktop / WSL2 integration

PowerShell:

```powershell
docker version
docker info
```

WSL2:

```bash
docker version
docker compose version
```

Success: both client and server are visible from WSL2.

## 6. WSL2 — build sandbox image

```bash
docker build -t repoatlas-sandbox:latest sandbox
```

Success: image builds. No repo code is executed yet.

## 7. WSL2 — start local infrastructure

```bash
docker compose up -d qdrant postgres phoenix
docker compose ps
```

Expected: Qdrant 6333/6334, Postgres 5432, Phoenix 6006/4317 running. These services are optional for the deterministic fixture smoke run but required for the full infrastructure validation.

## 8. WSL2 — deterministic fixture smoke path first

```bash
python -m scripts.create_fixture_repo
python -m scripts.parse_repository --repo data/fixture_repo
python -m scripts.build_index --repo data/fixture_repo --embedding hash
python -m scripts.build_graph --repo data/fixture_repo
python -m scripts.build_benchmark
python -m scripts.validate_benchmark
pytest -q
python -m scripts.security_smoke
python -m scripts.run_full_evaluation --fixture
```

Expected files:

- `data/processed/fixture_repo/symbols.json`
- `data/processed/fixture_repo/chunks.json`
- `data/processed/fixture_repo/index_manifest.json`
- `data/processed/fixture_repo/graph.graphml`
- `data/evaluation/dev/fixture-cache-001.json`
- `reports/experiments/*.json`

This proves the parser/retrieval/graph/evaluation plumbing before expensive downloads.

## 9. WSL2 — clone the default public target (HTTPX)

```bash
python -m scripts.clone_demo_repo
cd data/repositories/httpx
git rev-parse HEAD
git remote -v
cd ../../..
```

Record the commit hash. For reproducible benchmark cases, never evaluate against a moving `HEAD`; each case must store a base commit before the gold fix.

## 10. WSL2 — freeze a repository snapshot

```bash
python -m scripts.build_snapshot \
  --repo data/repositories/httpx \
  --dest data/snapshots/httpx \
  --base-commit HEAD
```

For historical benchmark cases replace `HEAD` with the pre-fix commit.

## 11. WSL2 — parse/symbol extraction

```bash
python -m scripts.parse_repository --repo data/snapshots/httpx
```

Success: non-zero symbol/chunk counts and JSON in `data/processed/httpx/`.

## 12. WSL2 + GPU — install GPU extras and verify PyTorch

Install the PyTorch wheel recommended by the current PyTorch CUDA selector for your driver/WSL combination, then:

```bash
pip install -e '.[gpu]'
python - <<'PY'
import torch
print('torch', torch.__version__)
print('cuda', torch.version.cuda)
print('available', torch.cuda.is_available())
print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
print('bf16', torch.cuda.is_bf16_supported() if torch.cuda.is_available() else None)
PY
```

Do not proceed to large-model inference unless CUDA is true and the RTX 5090 is visible.

## 13. WSL2 + GPU — build BGE dense index

```bash
python -m scripts.build_index --repo data/snapshots/httpx --embedding bge
python -m scripts.build_qdrant_index --repo data/snapshots/httpx --embedding bge --mode url
```

First run downloads `BAAI/bge-m3`. Watch VRAM and system RAM. Generated manifest is under `data/processed/httpx/`.

## 14. WSL2 — build graph

```bash
python -m scripts.build_graph --repo data/snapshots/httpx
```

Inspect `graph_summary.json`; graph size should be non-zero.

## 15. WSL2 + GPU — local model server (safe first-run model)

Create a dedicated vLLM environment if desired. Start with Qwen3-8B:

```bash
vllm serve Qwen/Qwen3-8B \
  --host 127.0.0.1 \
  --port 8000 \
  --dtype bfloat16 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.88
```

In another WSL2 terminal:

```bash
curl http://127.0.0.1:8000/v1/models
```

Only after the full pipeline is stable, benchmark the requested primary candidate:

```bash
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  --host 127.0.0.1 \
  --port 8000 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.94
```

The 30.5B FP8 checkpoint is expected to be tight on ~32 GB VRAM. If vLLM OOMs, send the entire server log; do not force a larger KV cache. RepoAtlas remains valid with Qwen3-8B as the fallback benchmark.

## 16. WSL2 — read-only investigation

```bash
python -m scripts.investigate \
  --repo data/snapshots/httpx \
  --task "Changing timeout behavior appears to affect request handling. Identify likely files, symbols, dependencies, and related tests." \
  --embedding bge \
  --reranker heuristic \
  --graph-hops 2
```

For higher-quality reranking, change `--reranker bge` after `BAAI/bge-reranker-v2-m3` is installed/downloaded.

## 17. WSL2 — V0/V1/V2/V3 retrieval evaluation

For real historical cases, add case JSON files under `data/evaluation/dev/` and use the same metric code. Fixture sanity commands:

```bash
python -m scripts.evaluate_retrieval
python -m scripts.evaluate_graph
python -m scripts.evaluate_agent
python -m scripts.safe_patch_fixture --docker
python -m scripts.compile_ablation
python -m scripts.failure_analysis
```

## 18. Graph-depth ablation

```bash
python -m scripts.evaluate_graph
```

Expected report: `reports/experiments/graph_ablation_fixture.json`. Real benchmark expansion must compare 0-hop vs 1-hop vs 2-hop on the same frozen cases.

## 19. Safe patch workflow

Write mode remains disabled by default. Before enabling it, complete the read-only benchmark and review results. Then set in `.env`:

```text
ENABLE_WRITE_TOOLS=true
```

Build a temporary workspace only; never point patch tools at the original target clone. The implementation uses `repoatlas.sandbox.manager.create_workspace`, `patching.application`, Docker test tools, and `patching.verifier`.

## 20. Docker sandbox verification

```bash
docker run --rm --network none --security-opt no-new-privileges \
  --cpus 2 --memory 4g --pids-limit 128 \
  repoatlas-sandbox:latest python -c "print('sandbox-ok')"
```

No host credentials or Docker socket should be mounted.

## 21. MCP check

```bash
python -m repoatlas.mcp.server --repo data/snapshots/httpx
```

Connect with an MCP inspector/client separately. The adapter exposes read-only file/exact-search/directory tools by default.

## 22. Observability

Open Phoenix locally at `http://localhost:6006`. RepoAtlas has lightweight local spans by default; wire OTLP export to Phoenix when running GPU/agent experiments so retrieval IDs, durations, model, graph nodes, tool calls, and outcomes can be retained.

## 23. API

```bash
uvicorn repoatlas.api.main:app --reload --host 127.0.0.1 --port 8080
```

Check:

```bash
curl http://127.0.0.1:8080/health
```

Then POST `/repositories/index` and `/tasks/investigate` using Swagger at `/docs`.

## 24. Gradio UI

```bash
python app/gradio_app.py
```

Use a local repository path, index it, and run read-only investigation. Capture screenshots only after real results are available.

## 25. What to send back after the first complete run

Please return these exact artifacts/logs:

1. `reports/environment_report.json` or terminal output.
2. fixture `pytest -q` summary.
3. `data/processed/httpx/graph_summary.json`.
4. parser/symbol count output.
5. benchmark validation output.
6. V0→V3 retrieval JSON and graph ablation JSON.
7. any V4/V5/V6 benchmark outputs you add for historical cases.
8. vLLM startup log + `nvidia-smi` during inference.
9. Docker sandbox build/run output.
10. `scripts.security_smoke` output.
11. API `/health` and one `/tasks/investigate` response.
12. any errors in full, without trimming the traceback.

We will tune DEV results and preserve the frozen TEST split for final measurement.
