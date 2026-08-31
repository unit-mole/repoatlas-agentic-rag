SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories(repository_id TEXT PRIMARY KEY,name TEXT,path TEXT,commit_hash TEXT);
CREATE TABLE IF NOT EXISTS chunks(chunk_id TEXT PRIMARY KEY,repository_id TEXT,file_path TEXT,qualified_symbol TEXT,content TEXT,metadata_json TEXT);
CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY,status TEXT,payload_json TEXT,created_at TEXT);
"""
