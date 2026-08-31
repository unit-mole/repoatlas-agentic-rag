import json

from repoatlas.database.models import SCHEMA
from repoatlas.database.session import connect


def initialize_db():
    con = connect()
    con.executescript(SCHEMA)
    con.commit()
    con.close()


def save_chunks(chunks):
    con = connect()
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?)",
        [
            (
                c.chunk_id,
                c.repository_id,
                c.file_path,
                c.qualified_symbol,
                c.content,
                json.dumps(c.model_dump(exclude={"content"}, mode="json")),
            )
            for c in chunks
        ],
    )
    con.commit()
    con.close()
