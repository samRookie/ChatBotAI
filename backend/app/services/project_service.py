"""Project management service for ChatbotAI Stage 3 Phase 1.

Provides project CRUD operations, conversation association, and atomic
hard-deletion cascade with explicit sqlite-vec virtual table cleanup.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from app.db.connection import get_connection

logger = logging.getLogger(__name__)


def create_project(name: str, description: str | None = None) -> dict:
    """Create a new project with a standard UUID string identifier."""
    if not name or not str(name).strip():
        raise ValueError("Project name must be a non-empty string")

    clean_name = name.strip()
    clean_desc = description.strip() if description is not None else None
    project_id = str(uuid.uuid4())

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
            (project_id, clean_name, clean_desc),
        )
        conn.commit()

        cursor.execute(
            "SELECT id, name, description, updated_at FROM projects WHERE id = ?",
            (project_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise sqlite3.DatabaseError(f"Failed to fetch newly created project {project_id}")
        return dict(row)
    finally:
        conn.close()


def list_projects() -> list[dict]:
    """List all projects ordered by updated_at descending."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description, updated_at FROM projects ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_project(project_id: str) -> dict | None:
    """Fetch project metadata by ID."""
    if not project_id or not str(project_id).strip():
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description, updated_at FROM projects WHERE id = ?",
            (project_id.strip(),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_project_detail(project_id: str) -> dict | None:
    """Fetch project metadata along with conversation count and associated conversation IDs."""
    if not project_id or not str(project_id).strip():
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description, updated_at FROM projects WHERE id = ?",
            (project_id.strip(),),
        )
        proj_row = cursor.fetchone()
        if proj_row is None:
            return None

        cursor.execute(
            "SELECT id FROM conversations WHERE project_id = ? ORDER BY created_at ASC",
            (project_id.strip(),),
        )
        conv_rows = cursor.fetchall()
        conversation_ids = [row["id"] for row in conv_rows]

        data = dict(proj_row)
        data["conversation_count"] = len(conversation_ids)
        data["conversation_ids"] = conversation_ids
        return data
    finally:
        conn.close()


def delete_project(project_id: str) -> bool:
    """Atomically hard-delete a project and all associated data.

    Executes in a single database transaction:
    1. Identifies all project-owned memory_chunks rowids.
    2. Explicitly deletes matching memory_vectors rows from the virtual table.
    3. Deletes project-owned conversations and their messages.
    4. Deletes project-owned memory_chunks.
    5. Deletes the project record itself.
    6. Commits the transaction (or rolls back completely on any failure).
    """
    if not project_id or not str(project_id).strip():
        return False

    pid = project_id.strip()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # 1. Verify existence
        cursor.execute("SELECT id FROM projects WHERE id = ?", (pid,))
        if cursor.fetchone() is None:
            return False

        # 2. Identify all memory_chunk rowids belonging to the project
        cursor.execute(
            """
            SELECT id FROM memory_chunks
            WHERE project_id = ?
               OR conversation_id IN (SELECT id FROM conversations WHERE project_id = ?)
            """,
            (pid, pid),
        )
        chunk_rows = cursor.fetchall()
        chunk_ids = [row["id"] for row in chunk_rows]

        # 3. Explicitly delete virtual table rows from memory_vectors
        if chunk_ids:
            placeholders = ", ".join(["?"] * len(chunk_ids))
            cursor.execute(
                f"DELETE FROM memory_vectors WHERE rowid IN ({placeholders})",
                chunk_ids,
            )

        # 4. Explicitly delete messages belonging to project conversations
        cursor.execute(
            """
            DELETE FROM messages
            WHERE conversation_id IN (SELECT id FROM conversations WHERE project_id = ?)
            """,
            (pid,),
        )

        # 5. Explicitly delete memory_chunks
        cursor.execute(
            """
            DELETE FROM memory_chunks
            WHERE project_id = ?
               OR conversation_id IN (SELECT id FROM conversations WHERE project_id = ?)
            """,
            (pid, pid),
        )

        # 6. Explicitly delete conversations
        cursor.execute("DELETE FROM conversations WHERE project_id = ?", (pid,))

        # 7. Delete the project itself
        cursor.execute("DELETE FROM projects WHERE id = ?", (pid,))

        conn.commit()
        logger.info("Project %s and all associated resources hard-deleted successfully.", pid)
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("Failed to delete project %s: %s (transaction rolled back)", pid, exc, exc_info=True)
        raise
    finally:
        conn.close()
