import sqlite3
from pathlib import Path

import sqlite_vec

DB_PATH = Path(__file__).resolve().parents[2] / "chatbot.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL DEFAULT 'owner',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    project_id TEXT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_chunks (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    project_id TEXT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
    embedding float[768]
);
"""


def load_sqlite_vec(connection: sqlite3.Connection) -> None:
    connection.enable_load_extension(True)
    try:
        sqlite_vec.load(connection)
    finally:
        connection.enable_load_extension(False)


def _migrate_columns(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(conversations)")
    conv_columns = {row["name"] for row in cursor.fetchall()}
    if conv_columns and "project_id" not in conv_columns:
        cursor.execute(
            "ALTER TABLE conversations ADD COLUMN project_id TEXT NULL REFERENCES projects(id) ON DELETE CASCADE"
        )

    cursor.execute("PRAGMA table_info(memory_chunks)")
    mem_columns = {row["name"] for row in cursor.fetchall()}
    if mem_columns and "project_id" not in mem_columns:
        cursor.execute(
            "ALTER TABLE memory_chunks ADD COLUMN project_id TEXT NULL REFERENCES projects(id) ON DELETE CASCADE"
        )


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    _migrate_columns(conn)
    conn.commit()


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    load_sqlite_vec(conn)
    _init_tables(conn)
    return conn


