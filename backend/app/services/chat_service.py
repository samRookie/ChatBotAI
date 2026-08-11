import sqlite3
import uuid
from datetime import datetime, timezone

from app.db.connection import get_connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_conversation_exists(
    session_id: str, conversation_id: str
) -> str:
    if not session_id:
        session_id = uuid.uuid4().hex
    if not conversation_id:
        conversation_id = uuid.uuid4().hex

    now = _utc_now()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, session_type, created_at) VALUES (?, ?, ?)",
            (session_id, "owner", now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, session_id, created_at) VALUES (?, ?, ?)",
            (conversation_id, session_id, now),
        )
        conn.commit()
    finally:
        conn.close()

    return conversation_id


def save_message(conversation_id: str, role: str, content: str) -> dict:
    message = {
        "id": uuid.uuid4().hex,
        "role": role,
        "content": content,
        "created_at": _utc_now(),
    }

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (message["id"], conversation_id, role, content, message["created_at"]),
        )
        conn.commit()
    finally:
        conn.close()

    return message


def delete_message(message_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
    finally:
        conn.close()


def get_conversation_history(conversation_id: str, limit: int = 50) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM (
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            )
            ORDER BY created_at ASC
            """,
            (conversation_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
