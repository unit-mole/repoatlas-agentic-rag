from pathlib import Path

from repoatlas.agents.graph import InvestigationEngine
from repoatlas.embeddings.bge import BGEEmbeddingProvider, HashEmbeddingProvider
from repoatlas.graph.builder import RepositoryGraphBuilder
from repoatlas.parsing.chunks import symbols_to_chunks
from repoatlas.parsing.symbols import extract_repository_symbols
from repoatlas.reranking.reranker import BGEReranker, HeuristicReranker
from repoatlas.retrieval.dense import DenseIndex
from repoatlas.retrieval.hybrid import HybridRetriever
from repoatlas.retrieval.lexical import BM25Index


def build_runtime(repo: Path, embedding="hash", reranker="heuristic"):
    symbols = extract_repository_symbols(repo.name, repo)
    chunks = symbols_to_chunks(symbols)
    emb = HashEmbeddingProvider() if embedding == "hash" else BGEEmbeddingProvider()
    lex = BM25Index(chunks)
    dense = DenseIndex(chunks, emb)
    hybrid = HybridRetriever(lex, dense)
    rr = HeuristicReranker() if reranker == "heuristic" else BGEReranker()
    graph = RepositoryGraphBuilder(symbols).build(repo)
    return {
        "symbols": symbols,
        "chunks": chunks,
        "lexical": lex,
        "dense": dense,
        "hybrid": hybrid,
        "reranker": rr,
        "graph": graph,
        "engine": InvestigationEngine(hybrid, rr, graph, chunks),
    }
