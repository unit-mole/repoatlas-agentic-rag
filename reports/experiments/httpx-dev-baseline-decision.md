# HTTPX DEV Baseline Decision

## Benchmark

Five historical HTTPX DEV cases evaluated from frozen pre-fix
repository snapshots with evaluator-only historical gold.

## Primary retrieval

V2 Hybrid (BM25 + BGE-M3 RRF) is the current primary retrieval
baseline.

Macro results:

- File Recall@5: 0.689
- File Recall@10: 0.861
- File MRR: 0.900
- File nDCG@10: 0.770
- Direct Test Recall@10: 0.700
- Retrieval latency: ~27.9 ms

## Dense retrieval

V1 BGE-M3 improves symbol localization compared with lexical
retrieval but does not outperform V2 on primary file localization.

## Reranker

V3 BGE reranking improves macro symbol localization:

- Symbol Recall@5: 0.757
- Symbol Recall@10: 0.819

However:

- File Recall@10 falls to 0.689.
- File nDCG@10 falls to 0.620.
- Mean reranking latency is ~3712 ms.

Decision:

Do not use V3 as a replacement for V2 global file ranking.
Evaluate it later as selective symbol refinement.

## Initial graph ranking

The original V4 graph-ranking strategy does not outperform V2.

Macro:

- File Recall@5: 0.494
- File Recall@10: 0.711
- nDCG@10: 0.582

Decision:

Do not allow graph expansion to freely replace strong direct
retrieval results.

Next experiment:

Protect strong V2 direct results and use graph traversal as bounded
augmentation/evidence.

## Changed-test discovery

Using reverse TESTS edges:

V2 Hybrid seeds:

- Changed-Test Recall@10: 0.700
- Changed-Test Recall@20: 1.000
- Changed-Test MRR: 0.478

V3 reranked seeds:

- Changed-Test Recall@10: 0.700
- Changed-Test Recall@20: 1.000
- Changed-Test MRR: 0.480

Decision:

Use V2 as the default test-discovery source because V3 provides
negligible aggregate benefit relative to its computational cost.

## Benchmark policy

These conclusions apply to the DEV benchmark only.

No architecture tuning will be performed using the future frozen TEST
benchmark.

## Protected Graph Augmentation — V4P

A protected graph variant was evaluated after the original unrestricted
V4 graph ranking degraded primary retrieval.

Design:

- Start from V2 Hybrid rather than V3.
- Preserve all available V2 direct results through the top-10 evaluation
  cutoff.
- Use the top V2 symbols as graph seeds.
- Apply deterministic bounded one-hop graph expansion.
- Graph evidence may fill positions after the protected direct prefix.
- Graph candidates do not replace protected V2 results.

Five-case DEV macro results:

V2:
- File Recall@5: 0.689
- File Recall@10: 0.861
- File Recall@20: 0.861
- Symbol Recall@5: 0.465
- Symbol Recall@10: 0.683
- Symbol Recall@20: 0.794
- File MRR: 0.900
- File nDCG@10: 0.770

V4P:
- File Recall@5: 0.689
- File Recall@10: 0.861
- File Recall@20: 0.883
- Symbol Recall@5: 0.465
- Symbol Recall@10: 0.683
- Symbol Recall@20: 0.794
- File MRR: 0.900
- File nDCG@10: 0.770

Latency:
- Mean graph-only stage: ~0.702 ms
- Mean V2 + protected graph end-to-end: ~31.032 ms

Decision:

Retain V4P as RepoAtlas graph augmentation.

The graph is used to broaden investigation context while V2 remains
authoritative for primary retrieval. V4P is not a replacement ranking
stage.

## Selective Symbol Reranking — V3S

A selective BGE cross-encoder experiment was evaluated after global
V3 reranking improved symbol localization but degraded file ranking
and introduced high latency.

Design:

- V2 Hybrid remains authoritative for file ranking.
- Select only symbols belonging to the strongest V2 files.
- Score at most 12 candidates with BAAI/bge-reranker-v2-m3.
- Use the reranker only to refine symbol ordering.
- Never allow V3S to modify V2 file ranking.

Five-case DEV macro results:

V2:
- File Recall@10: 0.861
- Symbol Recall@5: 0.465
- Symbol Recall@10: 0.683
- Symbol Recall@20: 0.794

V3S:
- File Recall@10: 0.861
- Symbol Recall@5: 0.669
- Symbol Recall@10: 0.683
- Symbol Recall@20: 0.794

Latency:
- Mean V2 retrieval: ~34.4 ms
- Mean V3S reranker stage: ~1277.4 ms
- Mean V3S end-to-end: ~1311.9 ms

Decision:

Retain V3S as an optional deep-investigation symbol-refinement stage.

V3S is not part of the default fast retrieval path because its primary
benefit is improved top-5 symbol localization while Symbol Recall@10
and Recall@20 remain unchanged.

The default retrieval path remains V2 + V4P + TESTS discovery.
