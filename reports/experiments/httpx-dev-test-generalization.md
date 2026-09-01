# RepoAtlas Retrieval Generalization Report

## Evaluation Protocol

RepoAtlas retrieval development was performed exclusively on five
historical HTTPX DEV cases.

Before TEST evaluation:

- the retrieval architecture was frozen;
- the configuration was checksummed;
- TEST selection policy was predeclared;
- five TEST cases were selected before retrieval scoring;
- TEST case definitions and evaluator-only gold patches were frozen;
- exact BASE snapshots were created without Git history;
- TEST parsing and graph artifacts were validated;
- TEST evaluation runners were committed before scoring.

No retrieval parameter was changed after observing TEST results.

Frozen configuration:

- `configs/retrieval_frozen_v1.json`
- SHA-256:
  `57e20457c7728d3886f6914f63d4f4aef711cd85b262e24606ca09199a2a14b6`

## V2 Hybrid Retrieval

V2 combines BM25 lexical retrieval and BGE-M3 dense retrieval using
reciprocal-rank fusion.

### DEV

- File Recall@5: 0.689
- File Recall@10: 0.861
- File Recall@20: 0.861
- Symbol Recall@5: 0.465
- Symbol Recall@10: 0.683
- Symbol Recall@20: 0.794
- File MRR: 0.900
- File nDCG@10: 0.770

### TEST

- File Recall@5: 0.729
- File Recall@10: 0.757
- File Recall@20: 0.843
- Symbol Recall@5: 0.350
- Symbol Recall@10: 0.400
- Symbol Recall@20: 0.400
- File MRR: 0.583
- File nDCG@10: 0.593

### Interpretation

V2 generalized reasonably at file localization depth.

File Recall@20 remained strong at 0.843 on unseen TEST cases, while
top-ranked file quality declined relative to DEV.

Symbol-level generalization was substantially harder, particularly on
historical changes whose exact changed symbols were weakly represented
by issue wording.

V2 remains RepoAtlas's authoritative primary retrieval stage.

## V4P Protected Graph Augmentation

### DEV

V4P preserved the primary V2 ranking and improved macro File Recall@20:

- V2 File Recall@20: 0.861
- V4P File Recall@20: 0.883

### TEST

- V2 File Recall@10: 0.757
- V4P File Recall@10: 0.757
- V2 File Recall@20: 0.843
- V4P File Recall@20: 0.843
- V2 Symbol Recall@20: 0.400
- V4P Symbol Recall@20: 0.400

### Interpretation

V4P caused no regression on the unseen TEST benchmark but produced no
aggregate localization improvement on these five cases.

V4P is retained as bounded investigation-context augmentation rather
than as a replacement ranking stage.

## V3S Selective Symbol Reranker

### DEV

- V2 Symbol Recall@5: 0.465
- V3S Symbol Recall@5: 0.669
- V2 Symbol Recall@10: 0.683
- V3S Symbol Recall@10: 0.683

### TEST

- V2 Symbol Recall@5: 0.350
- V3S Symbol Recall@5: 0.272
- V2 Symbol Recall@10: 0.400
- V3S Symbol Recall@10: 0.422
- V2 Symbol Recall@20: 0.400
- V3S Symbol Recall@20: 0.422

Latency:

- Mean V2 retrieval: 33.3 ms
- Mean V3S reranker stage: 938.2 ms
- Mean V3S end-to-end: 971.5 ms

### Interpretation

The strong DEV Symbol Recall@5 improvement did not generalize to TEST.

V3S slightly improved deeper Symbol Recall@10/@20 on TEST but reduced
top-5 symbol recall and added substantial latency.

V3S therefore remains an optional deep-investigation capability and is
not used in the default fast retrieval path.

No post-TEST tuning was performed.

## Changed-Test Discovery

### DEV — V2 source

- Recall@10: 0.700
- Recall@20: 1.000
- MRR: 0.478

### TEST — V2 source

- Recall@10: 0.667
- Recall@20: 0.933
- MRR: 0.360

### TEST — V3 source

- Recall@10: 0.467
- Recall@20: 0.700
- MRR: 0.450

### Interpretation

V2 generalized substantially better than V3 for changed-test coverage.

V3 occasionally ranked an identified test higher, producing higher MRR,
but missed considerably more historical changed tests overall.

V2 remains the default source for RepoAtlas test discovery.

## Final Retrieval Architecture

### Fast / Default Investigation

Issue
→ V2 BM25 + BGE-M3 Hybrid Retrieval
→ V4P protected graph context
→ V2-seeded reverse TESTS discovery

### Deep Investigation

Issue
→ V2
→ V4P
→ TESTS discovery
→ optional V3S symbol refinement

## Final Decision

Retrieval experimentation is closed.

No additional tuning will be performed against the historical TEST
benchmark.

Observed TEST limitations are retained and reported as generalization
evidence rather than optimized away.
