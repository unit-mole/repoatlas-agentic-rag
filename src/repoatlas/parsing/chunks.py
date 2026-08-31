from hashlib import sha256

from repoatlas.schemas.symbols import CodeChunk, Symbol


def symbols_to_chunks(symbols: list[Symbol]) -> list[CodeChunk]:
    out = []
    for s in symbols:
        cid = sha256(
            f"{s.repository_id}:{s.file_path}:{s.qualified_symbol}:{s.start_line}".encode()
        ).hexdigest()[:24]
        out.append(CodeChunk(**s.model_dump(), chunk_id=cid))
    return out
