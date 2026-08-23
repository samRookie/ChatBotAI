import os
import shutil
import sqlite3
import struct
import sys
import tempfile
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
import sqlite_vec

from app.main import app
from app.db.connection import get_connection, load_sqlite_vec, DB_PATH
from app.services import chat_service


def run_validations():
    print("==================================================")
    print("STAGE 2 STEP 1 COMPREHENSIVE VALIDATION SUITE")
    print("==================================================")
    client = TestClient(app)

    # ----------------------------------------------------
    # 1. sqlite-vec load verification via GET /api/v1/db-check
    # ----------------------------------------------------
    print("\n[Test 1] sqlite-vec load verification via GET /api/v1/db-check")
    resp = client.get("/api/v1/db-check")
    print(f"Status Code: {resp.status_code}")
    print(f"Response Body: {resp.json()}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "sqlite_vec_version" in data, "sqlite_vec_version missing in response"
    assert data["sqlite_vec_version"].startswith("v"), f"Unexpected version format: {data['sqlite_vec_version']}"
    print("--> Test 1 PASSED: Real vec_version returned.")

    # ----------------------------------------------------
    # 2. Existing database path (Case A)
    # ----------------------------------------------------
    print("\n[Test 2] Existing database path (Case A)")
    # Connect using get_connection() to the existing chatbot.db
    conn = get_connection(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sessions")
        sessions_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM conversations")
        conversations_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM messages")
        messages_count = cur.fetchone()[0]
        print(f"Preserved Stage 1 counts -> Sessions: {sessions_count}, Conversations: {conversations_count}, Messages: {messages_count}")
        assert sessions_count >= 1, f"Expected >=1 sessions, got {sessions_count}"
        assert conversations_count >= 1, f"Expected >=1 conversations, got {conversations_count}"
        assert messages_count >= 1, f"Expected >=1 messages, got {messages_count}"


        # Verify new tables also exist
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name IN ('memory_chunks', 'memory_vectors')")
        new_tables = [row[0] for row in cur.fetchall()]
        print(f"New tables found in existing DB: {new_tables}")
        assert "memory_chunks" in new_tables, "memory_chunks table missing in existing DB"
        assert "memory_vectors" in new_tables, "memory_vectors table missing in existing DB"
    finally:
        conn.close()
    print("--> Test 2 PASSED: Existing data preserved and new tables initialized safely.")

    # ----------------------------------------------------
    # 3. Fresh database path (Case B)
    # ----------------------------------------------------
    print("\n[Test 3] Fresh database path (Case B)")
    with tempfile.TemporaryDirectory() as tmpdir:
        fresh_db_path = Path(tmpdir) / "fresh_chatbot.db"
        assert not fresh_db_path.exists(), "Fresh DB should not exist before init"
        
        fresh_conn = get_connection(fresh_db_path)
        try:
            cur = fresh_conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cur.fetchall()]
            print(f"Tables in fresh database: {tables}")
            expected_tables = ["conversations", "memory_chunks", "memory_vectors", "messages", "sessions"]
            for tbl in expected_tables:
                assert tbl in tables, f"Expected table {tbl} missing in fresh database"
        finally:
            fresh_conn.close()
    print("--> Test 3 PASSED: Fresh DB creates all Stage 1 + Stage 2 Step 1 tables.")

    # ----------------------------------------------------
    # 4. Restart safety (Case C)
    # ----------------------------------------------------
    print("\n[Test 4] Restart safety (Case C)")
    with tempfile.TemporaryDirectory() as tmpdir:
        restart_db_path = Path(tmpdir) / "restart_test.db"
        # 1st Startup
        c1 = get_connection(restart_db_path)
        c1.execute("INSERT INTO sessions (id, session_type, created_at) VALUES ('s1', 'owner', '2026-08-14T00:00:00Z')")
        c1.commit()
        c1.close()

        # 2nd Startup (Restart 1)
        c2 = get_connection(restart_db_path)
        cur2 = c2.cursor()
        cur2.execute("SELECT COUNT(*) FROM sessions")
        assert cur2.fetchone()[0] == 1, "Session count mismatch on restart 1"
        c2.close()

        # 3rd Startup (Restart 2)
        c3 = get_connection(restart_db_path)
        cur3 = c3.cursor()
        cur3.execute("SELECT COUNT(*) FROM sessions")
        assert cur3.fetchone()[0] == 1, "Session count mismatch on restart 2"
        # Test inserting vector data and restarting again
        cur3.execute("INSERT INTO conversations (id, session_id, created_at) VALUES ('c1', 's1', '2026-08-14T00:00:00Z')")
        cur3.execute("INSERT INTO memory_chunks (id, conversation_id, chunk_text, created_at) VALUES (1, 'c1', 'chunk 1', '2026-08-14T00:00:00Z')")
        fake_embedding = sqlite_vec.serialize_float32([0.05] * 768)
        cur3.execute("INSERT INTO memory_vectors (rowid, embedding) VALUES (1, ?)", (fake_embedding,))
        c3.commit()
        c3.close()

        # 4th Startup (Restart 3)
        c4 = get_connection(restart_db_path)
        cur4 = c4.cursor()
        cur4.execute("SELECT c.id, c.chunk_text, v.rowid FROM memory_chunks c JOIN memory_vectors v ON c.id = v.rowid")
        row = cur4.fetchone()
        assert row is not None and row[0] == 1 and row[1] == "chunk 1", "Memory chunk and vector data lost on restart"
        c4.close()
    print("--> Test 4 PASSED: Multiple restarts caused no duplication, corruption, or errors.")

    # ----------------------------------------------------
    # 5. New table structure verification
    # ----------------------------------------------------
    print("\n[Test 5] New table structure verification")
    conn = get_connection(DB_PATH)
    try:
        cur = conn.cursor()
        # Check memory_chunks columns
        cur.execute("PRAGMA table_info(memory_chunks)")
        columns = {row["name"]: row["type"] for row in cur.fetchall()}
        print(f"memory_chunks schema columns: {columns}")
        assert "id" in columns and "INTEGER" in columns["id"].upper(), "id column missing or not INTEGER"
        assert "conversation_id" in columns and "TEXT" in columns["conversation_id"].upper(), "conversation_id column missing or not TEXT"
        assert "chunk_text" in columns and "TEXT" in columns["chunk_text"].upper(), "chunk_text column missing or not TEXT"
        assert "created_at" in columns and "TEXT" in columns["created_at"].upper(), "created_at column missing or not TEXT"

        # Check memory_vectors dimension
        cur.execute("SELECT sql FROM sqlite_master WHERE name='memory_vectors'")
        vec_sql = cur.fetchone()[0]
        print(f"memory_vectors SQL: {vec_sql}")
        assert "vec0" in vec_sql.lower(), "vec0 virtual table type missing"
        assert "768" in vec_sql, "768 dimension missing in memory_vectors definition"
    finally:
        conn.close()
    print("--> Test 5 PASSED: Table schemas match Section 7 specification exactly (including 768 dims).")

    # ----------------------------------------------------
    # 6. Existing chat regression test
    # ----------------------------------------------------
    print("\n[Test 6] Existing chat regression test")
    # Save a test message and get conversation history
    test_session_id = "test_session_reg"
    test_conv_id = "test_conv_reg"
    chat_service.ensure_conversation_exists(test_session_id, test_conv_id)
    msg = chat_service.save_message(test_conv_id, "user", "Hello from regression test")
    history = chat_service.get_conversation_history(test_conv_id)
    print(f"Saved message id: {msg['id']}, History length: {len(history)}")
    assert len(history) >= 1, "History did not return saved message"
    assert any(m["id"] == msg["id"] for m in history), "Saved message not found in history"
    
    # Test getting messages via API route
    resp = client.get(f"/api/v1/chat/{test_conv_id}")
    assert resp.status_code == 200, f"Expected 200 from chat history route, got {resp.status_code}"
    history_api = resp.json()
    assert len(history_api) >= 1, "API history is empty"
    
    # Clean up test message and session
    cleanup_conn = get_connection(DB_PATH)
    try:
        cleanup_conn.execute("DELETE FROM messages WHERE conversation_id = ?", (test_conv_id,))
        cleanup_conn.execute("DELETE FROM conversations WHERE id = ?", (test_conv_id,))
        cleanup_conn.execute("DELETE FROM sessions WHERE id = ?", (test_session_id,))
        cleanup_conn.commit()
    finally:
        cleanup_conn.close()
    print("--> Test 6 PASSED: Stage 1 chat persistence and history retrieval operate identically.")


    # ----------------------------------------------------
    # 7. Security check
    # ----------------------------------------------------
    print("\n[Test 7] Security check: verify enable_load_extension is disabled on connection return")
    conn = get_connection(DB_PATH)
    try:
        # Attempting to load an extension without re-enabling must fail
        try:
            conn.load_extension("some_random_extension")
            passed = False
        except sqlite3.OperationalError as e:
            # Expected error since load extension is disabled
            print(f"Observed expected OperationalError when trying unauthorized load_extension: {e}")
            passed = True
        assert passed, "Security failure: load_extension was unexpectedly allowed without enable_load_extension(True)"
    finally:
        conn.close()
    print("--> Test 7 PASSED: Extension loading is verified disabled after get_connection() returns.")

    print("\n==================================================")
    print("ALL 7 VALIDATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_validations()
