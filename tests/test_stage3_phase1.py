"""Stage 3 Phase 1 Comprehensive Validation and Verification Test Suite.

Validates all 15 testing requirements from Section 15:
- Group 1: Database foundation (PRAGMA foreign_keys, projects table schema, no created_at, FK constraints)
- Group 2: Project CRUD (create with UUID, list, get-detail, 404 for missing)
- Group 3: Project-owned conversation binding & detail count
- Group 4: Memory tagging (explicit project_id, conversation inheritance, ownership conflict rejection)
- Group 5: General memory tagging (project_id IS NULL as first-class valid state)
- Group 6: Single-project retrieval isolation (Project A vs Project B vs General)
- Group 7: General chat retrieval (only NULL project_id)
- Group 8: Cross-project retrieval (A & B included, C & General excluded)
- Group 9: Hybrid retrieval (A + General, and project_ids=None + include_general edge case)
- Group 10: Project delete cascade (conversations, messages, chunks, vectors)
- Group 11: Direct memory_vectors virtual table verification after deletion
- Group 12: Atomic delete failure rollback (controlled failure injection)
- Group 13: Existing regression tests (Stage 1 and Stage 2 test suites)
- Group 14: Migration safety (fresh DB, existing pre-Stage-3 DB migration, repeated restarts)
- Group 15: SQL injection safety in dynamic project ID queries
"""

import os
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if (backend_dir / "app").exists():
    sys.path.insert(0, str(backend_dir))
elif (Path(__file__).resolve().parent / "app").exists():
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
import sqlite_vec

from app.main import app
from app.db.connection import get_connection, DB_PATH
from app.services import (
    chat_service,
    embedding_service,
    project_service,
    retrieval_service,
)


@pytest.fixture
def isolated_db(tmp_path):
    """Fixture providing a fresh isolated database path for each test."""
    db_file = tmp_path / "test_stage3_phase1.db"
    with patch("app.db.connection.DB_PATH", db_file):
        with patch("app.services.project_service.get_connection", lambda: get_connection(db_file)):
            with patch("app.services.embedding_service.get_connection", lambda: get_connection(db_file)):
                with patch("app.services.retrieval_service.get_connection", lambda: get_connection(db_file)):
                    with patch("app.services.chat_service.get_connection", lambda: get_connection(db_file)):
                        # Initialize schema
                        conn = get_connection(db_file)
                        conn.close()
                        yield db_file


@pytest.fixture
def client(isolated_db):
    """FastAPI TestClient bound to the isolated database."""
    return TestClient(app)


# ==============================================================================
# GROUP 1: Database Foundation & Schema Verification
# ==============================================================================
def test_group1_database_foundation(isolated_db):
    """Verify PRAGMA foreign_keys, projects table schema, absence of created_at, and FK constraints."""
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        # 1. Foreign keys must be enabled
        cur.execute("PRAGMA foreign_keys;")
        fk_status = cur.fetchone()[0]
        assert fk_status == 1, f"Expected PRAGMA foreign_keys = 1, got {fk_status}"

        # 2. Inspect projects table columns
        cur.execute("PRAGMA table_info(projects);")
        proj_cols = {row["name"]: row["type"].upper() for row in cur.fetchall()}
        assert "id" in proj_cols and "TEXT" in proj_cols["id"], "projects.id missing or not TEXT"
        assert "name" in proj_cols and "TEXT" in proj_cols["name"], "projects.name missing or not TEXT"
        assert "description" in proj_cols and "TEXT" in proj_cols["description"], "projects.description missing or not TEXT"
        assert "updated_at" in proj_cols, "projects.updated_at missing"

        # 3. Explicit check: created_at must NOT exist on projects
        assert "created_at" not in proj_cols, "CRITICAL: created_at must explicitly NOT exist on projects table"

        # 4. Check conversations.project_id
        cur.execute("PRAGMA table_info(conversations);")
        conv_cols = {row["name"]: row["type"].upper() for row in cur.fetchall()}
        assert "project_id" in conv_cols and "TEXT" in conv_cols["project_id"], "conversations.project_id missing or not TEXT"

        # 5. Check memory_chunks.project_id
        cur.execute("PRAGMA table_info(memory_chunks);")
        mem_cols = {row["name"]: row["type"].upper() for row in cur.fetchall()}
        assert "project_id" in mem_cols and "TEXT" in mem_cols["project_id"], "memory_chunks.project_id missing or not TEXT"

        # 6. Verify FK enforcement on live connection
        fk_failed = False
        try:
            cur.execute(
                "INSERT INTO conversations (id, session_id, project_id, created_at) VALUES ('c_invalid', 's1', 'non-existent-proj', '2026-08-17T00:00:00Z')"
            )
            conn.commit()
        except sqlite3.IntegrityError:
            fk_failed = True
        assert fk_failed, "Foreign key constraint on conversations.project_id failed to enforce"
    finally:
        conn.close()


# ==============================================================================
# GROUP 2: Project CRUD Endpoints
# ==============================================================================
def test_group2_project_crud(client):
    """Test create, list, get-detail, and 404 behavior for projects."""
    # 1. Create project
    create_payload = {"name": "Alpha Project", "description": "Core architecture project"}
    create_resp = client.post("/api/v1/projects", json=create_payload)
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
    data = create_resp.json()
    assert "id" in data
    # Verify ID is a valid UUID
    parsed_uuid = uuid.UUID(data["id"])
    assert str(parsed_uuid) == data["id"]
    assert data["name"] == "Alpha Project"
    assert data["description"] == "Core architecture project"
    assert "updated_at" in data
    proj_id = data["id"]

    # 2. List projects
    list_resp = client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    projects_list = list_resp.json()
    assert len(projects_list) >= 1
    assert any(p["id"] == proj_id and p["name"] == "Alpha Project" for p in projects_list)

    # 3. Get project detail
    detail_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == proj_id
    assert detail["name"] == "Alpha Project"
    assert detail["description"] == "Core architecture project"
    assert detail["conversation_count"] == 0
    assert detail["conversation_ids"] == []

    # 4. Missing project detail -> 404
    missing_resp = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert missing_resp.status_code == 404

    # 5. Missing project delete -> 404
    missing_del = client.delete(f"/api/v1/projects/{uuid.uuid4()}")
    assert missing_del.status_code == 404


# ==============================================================================
# GROUP 3: Project-Owned Conversation Association
# ==============================================================================
def test_group3_project_owned_conversation(client, isolated_db):
    """Test associating conversations with a project and verifying detail counts."""
    # Create project
    proj = project_service.create_project("Beta Project", "Testing conversation linkage")
    proj_id = proj["id"]

    # Create 2 conversations bound to this project
    conv1 = chat_service.ensure_conversation_exists("sess_1", "conv_beta_1", project_id=proj_id)
    conv2 = chat_service.ensure_conversation_exists("sess_1", "conv_beta_2", project_id=proj_id)
    # Create 1 general conversation (not in project)
    conv_gen = chat_service.ensure_conversation_exists("sess_1", "conv_gen_1", project_id=None)

    # Inspect conversations in DB
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, project_id FROM conversations WHERE id = ?", (conv1,))
        row1 = cur.fetchone()
        assert row1["project_id"] == proj_id

        cur.execute("SELECT id, project_id FROM conversations WHERE id = ?", (conv_gen,))
        row_gen = cur.fetchone()
        assert row_gen["project_id"] is None
    finally:
        conn.close()

    # Query project detail via API
    resp = client.get(f"/api/v1/projects/{proj_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["conversation_count"] == 2
    assert sorted(detail["conversation_ids"]) == sorted([conv1, conv2])


# ==============================================================================
# GROUP 4: Memory Tagging & Inheritance & Conflict Checking
# ==============================================================================
def test_group4_memory_tagging_and_inheritance(isolated_db):
    """Test explicit project_id, conversation inheritance, and conflict rejection."""
    proj_a = project_service.create_project("Project A")
    proj_b = project_service.create_project("Project B")

    conv_a = chat_service.ensure_conversation_exists("s1", "conv_a", project_id=proj_a["id"])
    conv_gen = chat_service.ensure_conversation_exists("s1", "conv_gen", project_id=None)

    dummy_vec = [0.1] * 768

    # 1. Explicit project_id on store_embedding
    rowid_1 = embedding_service.store_embedding(
        conversation_id=conv_a,
        chunk_text="Memory with explicit project A",
        embedding=dummy_vec,
        project_id=proj_a["id"],
    )

    # 2. Inheritance: project_id omitted -> inherits from conversation conv_a
    rowid_2 = embedding_service.store_embedding(
        conversation_id=conv_a,
        chunk_text="Memory with inherited project A",
        embedding=dummy_vec,
        project_id=None,
    )

    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM memory_chunks WHERE id = ?", (rowid_1,))
        assert cur.fetchone()["project_id"] == proj_a["id"]

        cur.execute("SELECT project_id FROM memory_chunks WHERE id = ?", (rowid_2,))
        assert cur.fetchone()["project_id"] == proj_a["id"]
    finally:
        conn.close()

    # 3. Ownership conflict rejection: conv_a is Project A, caller supplies Project B
    conflict_rejected = False
    try:
        embedding_service.store_embedding(
            conversation_id=conv_a,
            chunk_text="Conflicting memory",
            embedding=dummy_vec,
            project_id=proj_b["id"],
        )
    except ValueError as exc:
        conflict_rejected = True
        assert "Project ID mismatch" in str(exc)
    assert conflict_rejected, "Failed to reject explicit project_id conflict with conversation"

    # 4. Conflict rejection: general conversation with explicit project_id
    gen_conflict_rejected = False
    try:
        embedding_service.store_embedding(
            conversation_id=conv_gen,
            chunk_text="Conflicting general memory",
            embedding=dummy_vec,
            project_id=proj_a["id"],
        )
    except ValueError as exc:
        gen_conflict_rejected = True
        assert "Project ID mismatch" in str(exc)
    assert gen_conflict_rejected, "Failed to reject project_id assignment to general conversation"


# ==============================================================================
# GROUP 5: General Memory Tagging
# ==============================================================================
def test_group5_general_memory_tagging(isolated_db):
    """Storing memory with no project results in memory_chunks.project_id IS NULL."""
    conv_gen = chat_service.ensure_conversation_exists("s1", "conv_gen_g5", project_id=None)
    dummy_vec = [0.2] * 768

    rowid = embedding_service.store_embedding(
        conversation_id=conv_gen,
        chunk_text="General memory chunk",
        embedding=dummy_vec,
        project_id=None,
    )

    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT project_id FROM memory_chunks WHERE id = ?", (rowid,))
        row = cur.fetchone()
        assert row["project_id"] is None, f"Expected project_id IS NULL, got {row['project_id']}"
    finally:
        conn.close()


# ==============================================================================
# GROUP 6: Single-Project Retrieval Isolation (Primary Isolation Test)
# ==============================================================================
def test_group6_single_project_retrieval_isolation(isolated_db):
    """With memory in Project A, Project B, and General, query scoped to Project A returns only A."""
    proj_a = project_service.create_project("Project A")
    proj_b = project_service.create_project("Project B")

    conv_a = chat_service.ensure_conversation_exists("s1", "c_a", project_id=proj_a["id"])
    conv_b = chat_service.ensure_conversation_exists("s1", "c_b", project_id=proj_b["id"])
    conv_gen = chat_service.ensure_conversation_exists("s1", "c_gen", project_id=None)

    vec = [1.0] + [0.0] * 767

    id_a = embedding_service.store_embedding(conv_a, "Memory in Project A", vec, project_id=proj_a["id"])
    id_b = embedding_service.store_embedding(conv_b, "Memory in Project B", vec, project_id=proj_b["id"])
    id_gen = embedding_service.store_embedding(conv_gen, "General Memory", vec, project_id=None)

    # Retrieval scoped to Project A only
    results = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=[proj_a["id"]],
        include_general=False,
    )

    result_ids = [r.id for r in results]
    assert result_ids == [id_a], f"Expected only Project A ({id_a}), got {result_ids}"
    assert all(r.project_id == proj_a["id"] for r in results)


# ==============================================================================
# GROUP 7: General Chat Retrieval
# ==============================================================================
def test_group7_general_chat_retrieval(isolated_db):
    """Query with project_ids=None, include_general=False returns only project_id IS NULL memories."""
    proj_a = project_service.create_project("Project A")
    conv_a = chat_service.ensure_conversation_exists("s1", "c_a_g7", project_id=proj_a["id"])
    conv_gen = chat_service.ensure_conversation_exists("s1", "c_gen_g7", project_id=None)

    vec = [1.0] + [0.0] * 767

    id_a = embedding_service.store_embedding(conv_a, "Project A memory", vec, project_id=proj_a["id"])
    id_gen = embedding_service.store_embedding(conv_gen, "General chat memory", vec, project_id=None)

    results = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=None,
        include_general=False,
    )

    result_ids = [r.id for r in results]
    assert result_ids == [id_gen], f"Expected only General ({id_gen}), got {result_ids}"
    assert results[0].project_id is None


# ==============================================================================
# GROUP 8: Cross-Project Retrieval
# ==============================================================================
def test_group8_cross_project_retrieval(isolated_db):
    """With memory in Projects A, B, C, and General, query scoped to [A, B] returns only A & B."""
    proj_a = project_service.create_project("Project A")
    proj_b = project_service.create_project("Project B")
    proj_c = project_service.create_project("Project C")

    conv_a = chat_service.ensure_conversation_exists("s1", "c_a_g8", project_id=proj_a["id"])
    conv_b = chat_service.ensure_conversation_exists("s1", "c_b_g8", project_id=proj_b["id"])
    conv_c = chat_service.ensure_conversation_exists("s1", "c_c_g8", project_id=proj_c["id"])
    conv_gen = chat_service.ensure_conversation_exists("s1", "c_gen_g8", project_id=None)

    vec = [1.0] + [0.0] * 767

    id_a = embedding_service.store_embedding(conv_a, "Memory in Project A", vec, project_id=proj_a["id"])
    id_b = embedding_service.store_embedding(conv_b, "Memory in Project B", vec, project_id=proj_b["id"])
    id_c = embedding_service.store_embedding(conv_c, "Memory in Project C", vec, project_id=proj_c["id"])
    id_gen = embedding_service.store_embedding(conv_gen, "General Memory", vec, project_id=None)

    results = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=[proj_a["id"], proj_b["id"]],
        include_general=False,
    )

    result_ids = set(r.id for r in results)
    assert result_ids == {id_a, id_b}, f"Expected {id_a, id_b}, got {result_ids}"
    assert id_c not in result_ids
    assert id_gen not in result_ids


# ==============================================================================
# GROUP 9: Hybrid Retrieval & Degraded Edge Cases
# ==============================================================================
def test_group9_hybrid_retrieval(isolated_db):
    """Test hybrid retrieval (A + General) and handle edge cases safely."""
    proj_a = project_service.create_project("Project A")
    proj_b = project_service.create_project("Project B")

    conv_a = chat_service.ensure_conversation_exists("s1", "c_a_g9", project_id=proj_a["id"])
    conv_b = chat_service.ensure_conversation_exists("s1", "c_b_g9", project_id=proj_b["id"])
    conv_gen = chat_service.ensure_conversation_exists("s1", "c_gen_g9", project_id=None)

    vec = [1.0] + [0.0] * 767

    id_a = embedding_service.store_embedding(conv_a, "Memory A", vec, project_id=proj_a["id"])
    id_b = embedding_service.store_embedding(conv_b, "Memory B", vec, project_id=proj_b["id"])
    id_gen = embedding_service.store_embedding(conv_gen, "Memory Gen", vec, project_id=None)

    # 1. Hybrid: Project A + General
    results_hybrid = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=[proj_a["id"]],
        include_general=True,
    )
    result_ids = set(r.id for r in results_hybrid)
    assert result_ids == {id_a, id_gen}, f"Expected {id_a, id_gen}, got {result_ids}"
    assert id_b not in result_ids

    # 2. Edge case: project_ids=None and include_general=True -> degrades to general-only
    results_none_hybrid = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=None,
        include_general=True,
    )
    assert [r.id for r in results_none_hybrid] == [id_gen]

    # 3. Edge case: project_ids=[] and include_general=True -> degrades to general-only
    results_empty_hybrid = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=[],
        include_general=True,
    )
    assert [r.id for r in results_empty_hybrid] == [id_gen]

    # 4. Edge case: project_ids=[] and include_general=False -> returns empty list
    results_empty_strict = retrieval_service.search_similar_chunks(
        query_vector=vec,
        top_k=10,
        project_ids=[],
        include_general=False,
    )
    assert results_empty_strict == []


# ==============================================================================
# GROUP 10: Project Delete Cascade
# ==============================================================================
def test_group10_project_delete_cascade(client, isolated_db):
    """Verify deleting a project removes conversations, messages, chunks, and vectors."""
    proj = project_service.create_project("Project To Delete")
    proj_id = proj["id"]

    conv_id = chat_service.ensure_conversation_exists("s1", "conv_del", project_id=proj_id)
    msg = chat_service.save_message(conv_id, "user", "Message to be deleted")
    vec = [0.5] * 768
    chunk_id = embedding_service.store_embedding(conv_id, "Chunk to be deleted", vec, project_id=proj_id)

    # Also store a general conversation and memory to ensure they are untouched
    conv_gen = chat_service.ensure_conversation_exists("s1", "conv_stay", project_id=None)
    msg_gen = chat_service.save_message(conv_gen, "user", "General message stays")
    chunk_gen = embedding_service.store_embedding(conv_gen, "General chunk stays", vec, project_id=None)

    # Delete via API
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify DB state
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        # Project gone
        cur.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (proj_id,))
        assert cur.fetchone()[0] == 0

        # Conversation gone
        cur.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conv_id,))
        assert cur.fetchone()[0] == 0

        # Message gone
        cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg["id"],))
        assert cur.fetchone()[0] == 0

        # Memory chunk gone
        cur.execute("SELECT COUNT(*) FROM memory_chunks WHERE id = ?", (chunk_id,))
        assert cur.fetchone()[0] == 0

        # General resources still intact
        cur.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conv_gen,))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_gen["id"],))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM memory_chunks WHERE id = ?", (chunk_gen,))
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()


# ==============================================================================
# GROUP 11: Vector-Delete Verification (Direct Virtual Table Query)
# ==============================================================================
def test_group11_vector_delete_verification(isolated_db):
    """Explicitly verify memory_vectors virtual table rows are cleaned up on deletion."""
    proj = project_service.create_project("Project Vector Cleanup")
    proj_id = proj["id"]

    conv_id = chat_service.ensure_conversation_exists("s1", "c_vec_cleanup", project_id=proj_id)
    vec = [0.3] * 768
    chunk_id = embedding_service.store_embedding(conv_id, "Vector verification chunk", vec, project_id=proj_id)

    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        # Verify vector row exists before delete
        cur.execute("SELECT COUNT(*) FROM memory_vectors WHERE rowid = ?", (chunk_id,))
        assert cur.fetchone()[0] == 1, "Vector rowid missing before delete"
    finally:
        conn.close()

    # Perform hard delete
    deleted = project_service.delete_project(proj_id)
    assert deleted is True

    # Re-query virtual table directly
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_vectors WHERE rowid = ?", (chunk_id,))
        count = cur.fetchone()[0]
        assert count == 0, f"CRITICAL: memory_vectors rowid {chunk_id} was NOT deleted! Count: {count}"
    finally:
        conn.close()


# ==============================================================================
# GROUP 12: Atomic Delete Failure Rollback
# ==============================================================================
def test_group12_atomic_delete_failure_rollback(isolated_db):
    """Simulate failure during project deletion and confirm complete transaction rollback."""
    proj = project_service.create_project("Project Rollback Test")
    proj_id = proj["id"]

    conv_id = chat_service.ensure_conversation_exists("s1", "c_rollback", project_id=proj_id)
    msg = chat_service.save_message(conv_id, "user", "Rollback message")
    vec = [0.4] * 768
    chunk_id = embedding_service.store_embedding(conv_id, "Rollback chunk", vec, project_id=proj_id)

    class FlakyCursor:
        def __init__(self, real_cursor):
            self._cur = real_cursor

        def execute(self, sql, params=()):
            if "DELETE FROM messages" in sql:
                raise sqlite3.DatabaseError("Simulated database failure during messages deletion")
            return self._cur.execute(sql, params)

        def fetchone(self):
            return self._cur.fetchone()

        def fetchall(self):
            return self._cur.fetchall()

        def __getattr__(self, name):
            return getattr(self._cur, name)

    class FlakyConnection:
        def __init__(self, conn):
            self._conn = conn

        def cursor(self):
            return FlakyCursor(self._conn.cursor())

        def commit(self):
            return self._conn.commit()

        def rollback(self):
            return self._conn.rollback()

        def close(self):
            return self._conn.close()

        def __getattr__(self, name):
            return getattr(self._conn, name)

    with patch("app.services.project_service.get_connection", lambda: FlakyConnection(get_connection(isolated_db))):
        delete_failed = False
        try:
            project_service.delete_project(proj_id)
        except sqlite3.DatabaseError:
            delete_failed = True
        assert delete_failed, "Expected delete_project to raise simulated exception"

    # Verify rollback: everything must still exist
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (proj_id,))
        assert cur.fetchone()[0] == 1, "Project was deleted despite failure"

        cur.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conv_id,))
        assert cur.fetchone()[0] == 1, "Conversation was deleted despite failure"

        cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg["id"],))
        assert cur.fetchone()[0] == 1, "Message was deleted despite failure"

        cur.execute("SELECT COUNT(*) FROM memory_chunks WHERE id = ?", (chunk_id,))
        assert cur.fetchone()[0] == 1, "Memory chunk was deleted despite failure"

        cur.execute("SELECT COUNT(*) FROM memory_vectors WHERE rowid = ?", (chunk_id,))
        assert cur.fetchone()[0] == 1, "Memory vector was deleted despite failure"
    finally:
        conn.close()



# ==============================================================================
# GROUP 13: Existing Regression Verification
# ==============================================================================
def test_group13_existing_chat_and_memory_regression(client, isolated_db):
    """Verify Stage 1 chat persistence and Stage 2 memory reader/writer regression."""
    # Stage 1 chat
    session_id = "reg_s1"
    conv_id = "reg_c1"
    chat_service.ensure_conversation_exists(session_id, conv_id)
    msg = chat_service.save_message(conv_id, "user", "Regression user message")
    history = chat_service.get_conversation_history(conv_id)
    assert len(history) == 1
    assert history[0]["content"] == "Regression user message"

    # API chat history retrieval
    resp = client.get(f"/api/v1/chat/{conv_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Stage 2 db-check endpoint
    db_resp = client.get("/api/v1/db-check")
    assert db_resp.status_code == 200
    assert "sqlite_vec_version" in db_resp.json()


# ==============================================================================
# GROUP 14: Migration Safety & Idempotency
# ==============================================================================
def test_group14_migration_safety(tmp_path):
    """Test fresh DB initialization, pre-Stage-3 DB migration, and repeated restarts."""
    db_path = tmp_path / "migration_test.db"

    # 1. Create pre-Stage-3 schema (Stage 2 legacy DB) without projects or project_id
    raw_conn = sqlite3.connect(db_path)
    raw_conn.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            session_type TEXT NOT NULL DEFAULT 'owner',
            created_at TEXT NOT NULL
        );
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            created_at TEXT NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE memory_chunks (
            id INTEGER PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id),
            chunk_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    raw_conn.execute("INSERT INTO sessions VALUES ('s1', 'owner', '2026-08-14T00:00:00Z')")
    raw_conn.execute("INSERT INTO conversations VALUES ('c1', 's1', '2026-08-14T00:00:00Z')")
    raw_conn.execute("INSERT INTO messages VALUES ('m1', 'c1', 'user', 'legacy msg', '2026-08-14T00:00:00Z')")
    raw_conn.execute("INSERT INTO memory_chunks VALUES (1, 'c1', 'legacy chunk', '2026-08-14T00:00:00Z')")
    raw_conn.commit()
    raw_conn.close()

    # 2. Run get_connection which triggers automatic migration
    c1 = get_connection(db_path)
    cur1 = c1.cursor()

    # Verify existing data preserved
    cur1.execute("SELECT COUNT(*) FROM sessions")
    assert cur1.fetchone()[0] == 1
    cur1.execute("SELECT COUNT(*) FROM conversations")
    assert cur1.fetchone()[0] == 1
    cur1.execute("SELECT COUNT(*) FROM memory_chunks")
    assert cur1.fetchone()[0] == 1

    # Verify columns were added with NULL default for legacy data
    cur1.execute("SELECT project_id FROM conversations WHERE id = 'c1'")
    assert cur1.fetchone()["project_id"] is None
    cur1.execute("SELECT project_id FROM memory_chunks WHERE id = 1")
    assert cur1.fetchone()["project_id"] is None

    c1.close()

    # 3. Repeated initialization (Restart 1 & Restart 2)
    c2 = get_connection(db_path)
    c2.close()

    c3 = get_connection(db_path)
    cur3 = c3.cursor()
    cur3.execute("SELECT COUNT(*) FROM conversations")
    assert cur3.fetchone()[0] == 1
    cur3.execute("PRAGMA table_info(conversations)")
    cols = [r["name"] for r in cur3.fetchall()]
    assert cols.count("project_id") == 1, "Duplicate project_id column created on restart"
    c3.close()


# ==============================================================================
# GROUP 15: SQL Injection Safety in Dynamic Project Queries
# ==============================================================================
def test_group15_sql_injection_safety(isolated_db):
    """Pass malicious SQL strings as project IDs and verify inert parameterized treatment."""
    proj = project_service.create_project("Legitimate Project")
    conv = chat_service.ensure_conversation_exists("s1", "c_legit", project_id=proj["id"])
    vec = [1.0] + [0.0] * 767
    chunk_id = embedding_service.store_embedding(conv, "Legit chunk", vec, project_id=proj["id"])

    # Attempt SQL injection via project_ids
    malicious_ids = [
        "foo' OR 1=1 --",
        "'; DROP TABLE projects; --",
        "p1') UNION SELECT 1, 'x', 'y', 'z', 0.0 --",
    ]

    for attack_str in malicious_ids:
        # Must execute cleanly and return 0 matches without error or injection execution
        results = retrieval_service.search_similar_chunks(
            query_vector=vec,
            top_k=10,
            project_ids=[attack_str],
            include_general=False,
        )
        assert results == [], f"SQL injection attempt '{attack_str}' unexpectedly returned results or modified scope!"

    # Confirm database tables and projects are completely intact
    conn = get_connection(isolated_db)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projects")
        assert cur.fetchone()[0] >= 1
    finally:
        conn.close()


def run_stage3_phase1_tests():
    """Manual direct test execution runner with per-test DB isolation."""
    print("==================================================")
    print("STAGE 3 PHASE 1 COMPREHENSIVE TEST SUITE")
    print("==================================================")

    def run_isolated(test_fn, *args, **kwargs):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = Path(tmpdir) / "test_stage3_phase1.db"
            with patch("app.db.connection.DB_PATH", test_db):
                with patch("app.services.project_service.get_connection", lambda: get_connection(test_db)):
                    with patch("app.services.embedding_service.get_connection", lambda: get_connection(test_db)):
                        with patch("app.services.retrieval_service.get_connection", lambda: get_connection(test_db)):
                            with patch("app.services.chat_service.get_connection", lambda: get_connection(test_db)):
                                conn = get_connection(test_db)
                                conn.close()
                                if "client" in test_fn.__code__.co_varnames:
                                    client = TestClient(app)
                                    test_fn(client, *args, **kwargs)
                                elif "isolated_db" in test_fn.__code__.co_varnames:
                                    test_fn(test_db, *args, **kwargs)
                                elif "tmp_path" in test_fn.__code__.co_varnames:
                                    test_fn(Path(tmpdir), *args, **kwargs)
                                else:
                                    test_fn(*args, **kwargs)

    print("\n[Group 1] Database Foundation & PRAGMA foreign_keys...")
    run_isolated(test_group1_database_foundation)
    print("--> Group 1 PASSED")

    print("\n[Group 2] Project CRUD Endpoints...")
    run_isolated(test_group2_project_crud)
    print("--> Group 2 PASSED")

    print("\n[Group 3] Project-Owned Conversation Association...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_stage3_phase1.db"
        with patch("app.db.connection.DB_PATH", test_db):
            with patch("app.services.project_service.get_connection", lambda: get_connection(test_db)):
                with patch("app.services.embedding_service.get_connection", lambda: get_connection(test_db)):
                    with patch("app.services.retrieval_service.get_connection", lambda: get_connection(test_db)):
                        with patch("app.services.chat_service.get_connection", lambda: get_connection(test_db)):
                            conn = get_connection(test_db)
                            conn.close()
                            client = TestClient(app)
                            test_group3_project_owned_conversation(client, test_db)
    print("--> Group 3 PASSED")

    print("\n[Group 4] Memory Tagging, Inheritance & Conflict Rejection...")
    run_isolated(test_group4_memory_tagging_and_inheritance)
    print("--> Group 4 PASSED")

    print("\n[Group 5] General Memory Tagging...")
    run_isolated(test_group5_general_memory_tagging)
    print("--> Group 5 PASSED")

    print("\n[Group 6] Single-Project Retrieval Isolation...")
    run_isolated(test_group6_single_project_retrieval_isolation)
    print("--> Group 6 PASSED")

    print("\n[Group 7] General Chat Retrieval...")
    run_isolated(test_group7_general_chat_retrieval)
    print("--> Group 7 PASSED")

    print("\n[Group 8] Cross-Project Retrieval...")
    run_isolated(test_group8_cross_project_retrieval)
    print("--> Group 8 PASSED")

    print("\n[Group 9] Hybrid Retrieval & Edge Cases...")
    run_isolated(test_group9_hybrid_retrieval)
    print("--> Group 9 PASSED")

    print("\n[Group 10] Project Delete Cascade...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_stage3_phase1.db"
        with patch("app.db.connection.DB_PATH", test_db):
            with patch("app.services.project_service.get_connection", lambda: get_connection(test_db)):
                with patch("app.services.embedding_service.get_connection", lambda: get_connection(test_db)):
                    with patch("app.services.retrieval_service.get_connection", lambda: get_connection(test_db)):
                        with patch("app.services.chat_service.get_connection", lambda: get_connection(test_db)):
                            conn = get_connection(test_db)
                            conn.close()
                            client = TestClient(app)
                            test_group10_project_delete_cascade(client, test_db)
    print("--> Group 10 PASSED")

    print("\n[Group 11] Direct Vector-Delete Verification...")
    run_isolated(test_group11_vector_delete_verification)
    print("--> Group 11 PASSED")

    print("\n[Group 12] Atomic Delete Failure Rollback...")
    run_isolated(test_group12_atomic_delete_failure_rollback)
    print("--> Group 12 PASSED")

    print("\n[Group 13] Existing Regression Verification...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_stage3_phase1.db"
        with patch("app.db.connection.DB_PATH", test_db):
            with patch("app.services.project_service.get_connection", lambda: get_connection(test_db)):
                with patch("app.services.embedding_service.get_connection", lambda: get_connection(test_db)):
                    with patch("app.services.retrieval_service.get_connection", lambda: get_connection(test_db)):
                        with patch("app.services.chat_service.get_connection", lambda: get_connection(test_db)):
                            conn = get_connection(test_db)
                            conn.close()
                            client = TestClient(app)
                            test_group13_existing_chat_and_memory_regression(client, test_db)
    print("--> Group 13 PASSED")

    print("\n[Group 14] Migration Safety & Idempotency...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_group14_migration_safety(Path(tmpdir))
    print("--> Group 14 PASSED")

    print("\n[Group 15] SQL Injection Safety...")
    run_isolated(test_group15_sql_injection_safety)
    print("--> Group 15 PASSED")


    print("\n==================================================")
    print("ALL 15 STAGE 3 PHASE 1 TEST GROUPS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_stage3_phase1_tests()
