from repoatlas.embeddings.bge import HashEmbeddingProvider
from repoatlas.retrieval.dense import DenseIndex
from repoatlas.retrieval.hybrid import HybridRetriever
from repoatlas.retrieval.lexical import BM25Index
from repoatlas.schemas.symbols import CodeChunk


def chunks():
    base = {
        "repository_id": "r",
        "file_path": "x.py",
        "symbol_type": "function",
        "start_line": 1,
        "end_line": 2,
        "content_hash": "x",
    }
    return [
        CodeChunk(
            **base,
            chunk_id="1",
            name="refresh_token",
            qualified_symbol="refresh_token",
            content="refresh expired authentication token cache",
        ),
        CodeChunk(
            **base,
            chunk_id="2",
            name="render",
            qualified_symbol="render",
            content="render html template",
        ),
    ]


def test_bm25_exact():
    assert BM25Index(chunks()).search("refresh_token")[0].chunk_id == "1"


def test_hybrid():
    c = chunks()
    h = HybridRetriever(BM25Index(c), DenseIndex(c, HashEmbeddingProvider()))
    assert h.search("expired token")[0].chunk_id == "1"
