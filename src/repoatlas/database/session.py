import sqlite3
from pathlib import Path


def connect(path: Path = Path("data/repoatlas.db")):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con
