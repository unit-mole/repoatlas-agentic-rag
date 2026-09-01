# 2026 Stack Verification Notes

Verified against current official/model-card documentation before initial packaging:

- Qwen3-Coder-30B-A3B-Instruct and official FP8 checkpoint exist, Apache-2.0, 30.5B total / 3.3B active, vLLM-compatible. FP8 materially reduces weight memory but ~32 GB VRAM remains tight once inference overhead/KV cache is included.
- Qwen3-8B exists, Apache-2.0, vLLM-compatible, ~16.4 GB BF16 checkpoint size and is the safer first-run fallback.
- BAAI/bge-m3: MIT, 1024-d, max 8192 tokens; model documentation recommends hybrid retrieval + reranking.
- BAAI/bge-reranker-v2-m3: Apache-2.0 cross-encoder reranker.
- MCP Python SDK v2 is the current stable line in the checked 2026 documentation; Python 3.10+.
- Phoenix can be self-hosted for free and supports OTLP endpoints; SQLite and PostgreSQL storage modes exist.
- Qdrant documents local Docker operation on ports 6333/6334.
- LangGraph remains a low-level stateful orchestration framework and does not require stacking every LangChain ecosystem framework.
- HTTPX is BSD-licensed and documents a substantial test/lint workflow.
- Hugging Face Spaces conditions have changed: CPU Basic has no hourly hardware charge, but current documentation states creating new compute (Gradio/Docker) Spaces requires a paid plan; GPU hardware is paid unless a grant applies. Therefore HF deployment is optional and not part of RepoAtlas's zero-mandatory-paid-dependency claim. A static portfolio/case-study remains the guaranteed zero-cost fallback.
