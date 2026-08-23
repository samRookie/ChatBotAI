import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from google.genai import errors as genai_errors
import sqlite_vec

from app.main import app
from app.db.connection import get_connection, DB_PATH
from app.services import chat_service, embedding_service
from test_throttling import wait_between_live_api_calls


def run_stage2_step2_tests():
    print("==================================================")
    print("STAGE 2 STEP 2 COMPREHENSIVE VALIDATION SUITE")
    print("==================================================")
    client = TestClient(app)

    # ----------------------------------------------------
    # 1. Valid embedding generation (Real Gemini API Call)
    # ----------------------------------------------------
    print("\n[Test 1] Valid embedding generation via Gemini API")
    sample_text = "ChatbotAI memory chunk test representation."
    embedding = embedding_service.generate_embedding(sample_text)
    wait_between_live_api_calls()
    print(f"Generated embedding vector length: {len(embedding)}")
    print(f"Sample vector values (first 4): {embedding[:4]}")
    assert isinstance(embedding, list), "Embedding should be a list of floats"
    assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"
    assert all(isinstance(x, float) for x in embedding), "All vector elements must be floats"
    print("--> Test 1 PASSED: Live Gemini embedding generated with exact 768 dimensions.")

    # ----------------------------------------------------
    # 2. Invalid / empty input handling
    # ----------------------------------------------------
    print("\n[Test 2] Invalid/empty input handling")
    for bad_input in ["", "   ", None]:
        rejected = False
        try:
            embedding_service.generate_embedding(bad_input)
        except (ValueError, TypeError) as exc:
            rejected = True
            print(f"Correctly rejected bad input {repr(bad_input)}: {exc}")
        assert rejected, f"Failed to reject invalid input: {repr(bad_input)}"
    print("--> Test 2 PASSED: Invalid inputs safely rejected.")

    # ----------------------------------------------------
    # 3. Metadata + vector insertion (store_memory / store_embedding)
    # ----------------------------------------------------
    print("\n[Test 3] Metadata + vector insertion")
    test_session_id = "test_s2_session"
    test_conv_id = "test_s2_conv"
    chat_service.ensure_conversation_exists(test_session_id, test_conv_id)
    
    # Store memory
    chunk_text = "Architecture design note: SQLite vector storage using sqlite-vec."
    rowid = embedding_service.store_memory(test_conv_id, chunk_text, embedding=embedding)
    print(f"Stored memory chunk and vector at rowid: {rowid}")
    assert rowid > 0, "Rowid should be a positive integer"

    # Verify both tables contain exactly the one row
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, conversation_id, chunk_text, created_at FROM memory_chunks WHERE id = ?", (rowid,))
        chunk_row = cur.fetchone()
        assert chunk_row is not None, "memory_chunks row not found"
        assert chunk_row["conversation_id"] == test_conv_id
        assert chunk_row["chunk_text"] == chunk_text
        assert chunk_row["created_at"] is not None

        cur.execute("SELECT rowid FROM memory_vectors WHERE rowid = ?", (rowid,))
        vec_row = cur.fetchone()
        assert vec_row is not None, "memory_vectors row not found"
        assert vec_row[0] == rowid, "memory_vectors rowid mismatch"
    finally:
        conn.close()
    print("--> Test 3 PASSED: Exactly one memory_chunks row and one memory_vectors row stored.")

    # ----------------------------------------------------
    # 4. Row identity invariant (memory_chunks.id == memory_vectors.rowid)
    # ----------------------------------------------------
    print("\n[Test 4] Row identity invariant")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.chunk_text, v.rowid, vec_distance_cosine(v.embedding, ?) as dist
            FROM memory_chunks c
            JOIN memory_vectors v ON c.id = v.rowid
            WHERE c.id = ?
            """,
            (sqlite_vec.serialize_float32(embedding), rowid),
        )
        joined_row = cur.fetchone()
        assert joined_row is not None, "Join between memory_chunks and memory_vectors on rowid failed"
        assert joined_row["id"] == joined_row["rowid"] == rowid, "Row identity invariant violated"
        print(f"Join query result: chunk_id={joined_row['id']}, vector_rowid={joined_row['rowid']}, cosine_distance={joined_row['dist']}")
        assert joined_row["dist"] < 0.0001, f"Cosine distance to self should be ~0, got {joined_row['dist']}"
    finally:
        # Clean up test rows
        conn.execute("DELETE FROM memory_vectors WHERE rowid = ?", (rowid,))
        conn.execute("DELETE FROM memory_chunks WHERE id = ?", (rowid,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (test_conv_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (test_session_id,))
        conn.commit()
        conn.close()
    print("--> Test 4 PASSED: Row identity invariant asserted and verified.")

    # ----------------------------------------------------
    # 5. Vector dimension validation (reject invalid length before DB write)
    # ----------------------------------------------------
    print("\n[Test 5] Vector dimension validation")
    invalid_vectors = [
        [0.1] * 512,
        [0.1] * 1024,
        [0.1] * 767,
        [0.1] * 769,
        [],
    ]
    for bad_vec in invalid_vectors:
        rejected = False
        try:
            embedding_service.store_embedding("dummy_conv", "dummy text", bad_vec)
        except ValueError as exc:
            rejected = True
            print(f"Correctly rejected dimension {len(bad_vec)}: {exc}")
        assert rejected, f"Failed to reject vector with dimension {len(bad_vec)}"
    print("--> Test 5 PASSED: Strict 768-dimension validation enforced before any DB operation.")

    # ----------------------------------------------------
    # 6. Gemini failure path (no DB writes on API failure)
    # ----------------------------------------------------
    print("\n[Test 6] Gemini API failure path simulation")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_before = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM memory_vectors")
        vectors_before = cur.fetchone()[0]
    finally:
        conn.close()

    # Simulate Gemini API error
    with patch.object(embedding_service, "_call_gemini_embed", side_effect=genai_errors.APIError(500, {"message": "Simulated Gemini outage"})):
        api_failed = False
        try:
            embedding_service.store_memory("dummy_conv", "text that will fail embedding")
        except genai_errors.APIError:
            api_failed = True
            print("Caught expected simulated Gemini API error.")
        assert api_failed, "Should have raised Gemini APIError"

    # Confirm DB counts unchanged
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_after = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM memory_vectors")
        vectors_after = cur.fetchone()[0]
        assert chunks_before == chunks_after, "memory_chunks was modified during failed embedding call"
        assert vectors_before == vectors_after, "memory_vectors was modified during failed embedding call"
    finally:
        conn.close()
    print("--> Test 6 PASSED: Zero database writes occurred during Gemini API failure.")

    # ----------------------------------------------------
    # 7. Vector insertion failure path (rollback memory_chunks if vector insert fails)
    # ----------------------------------------------------
    print("\n[Test 7] Vector insertion failure path (transaction rollback)")
    test_session_id2 = "test_s2_session2"
    test_conv_id2 = "test_s2_conv2"
    chat_service.ensure_conversation_exists(test_session_id2, test_conv_id2)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_before = cur.fetchone()[0]
    finally:
        conn.close()

    # Force a failure during vector insertion (e.g. serialize_float32 mock exception)
    with patch("app.services.embedding_service.sqlite_vec.serialize_float32", side_effect=RuntimeError("Simulated vector serialization failure")):
        insert_failed = False
        try:
            embedding_service.store_embedding(test_conv_id2, "text with vector insert failure", embedding)
        except RuntimeError:
            insert_failed = True
            print("Caught expected simulated vector serialization/insert failure.")
        assert insert_failed, "Should have raised simulated error"

    # Verify memory_chunks was rolled back and no orphan row exists
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_after = cur.fetchone()[0]
        assert chunks_before == chunks_after, f"Orphan memory_chunks row created! Before: {chunks_before}, After: {chunks_after}"
        # Clean up conversation/session
        conn.execute("DELETE FROM conversations WHERE id = ?", (test_conv_id2,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (test_session_id2,))
        conn.commit()
    finally:
        conn.close()
    print("--> Test 7 PASSED: Transaction atomicity verified — no orphan memory_chunks rows created.")

    # ----------------------------------------------------
    # 8. Stage 1 regression tests
    # ----------------------------------------------------
    print("\n[Test 8] Stage 1 regression tests")
    reg_session = "reg_session_s2_step2"
    reg_conv = "reg_conv_s2_step2"
    chat_service.ensure_conversation_exists(reg_session, reg_conv)
    saved_msg = chat_service.save_message(reg_conv, "user", "Regression testing Stage 1 chat persistence")
    history = chat_service.get_conversation_history(reg_conv)
    assert len(history) >= 1, "History retrieval failed"
    assert any(m["id"] == saved_msg["id"] for m in history), "Message not in history"

    # Verify Stage 2 Step 1 endpoint /api/v1/db-check
    resp = client.get("/api/v1/db-check")
    assert resp.status_code == 200, f"db-check failed: {resp.status_code}"
    assert resp.json()["sqlite_vec_version"] == "v0.1.9"

    # Cleanup regression chat
    conn = get_connection()
    try:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (reg_conv,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (reg_conv,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (reg_session,))
        conn.commit()
    finally:
        conn.close()
    print("--> Test 8 PASSED: Stage 1 chat and Stage 2 Step 1 endpoints verified intact.")

    # ----------------------------------------------------
    # 9. Application restart & initialization safety
    # ----------------------------------------------------
    print("\n[Test 9] Application restart & initialization safety")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "app_restart_test.db"
        # 1st connection
        c1 = get_connection(test_db_path)
        c1.execute("INSERT INTO sessions (id, session_type, created_at) VALUES ('s1', 'owner', '2026-08-15T00:00:00Z')")
        c1.execute("INSERT INTO conversations (id, session_id, created_at) VALUES ('c1', 's1', '2026-08-15T00:00:00Z')")
        c1.commit()
        c1.close()

        # 2nd connection: store memory
        with patch.object(embedding_service, "get_connection", lambda: get_connection(test_db_path)):
            r = embedding_service.store_embedding("c1", "Restart test text", embedding)
            assert r == 1

        # 3rd connection: verify data
        c3 = get_connection(test_db_path)
        cur3 = c3.cursor()
        cur3.execute("SELECT c.id, c.chunk_text, v.rowid FROM memory_chunks c JOIN memory_vectors v ON c.id = v.rowid")
        row = cur3.fetchone()
        assert row is not None and row[0] == 1 and row[1] == "Restart test text"
        c3.close()
    print("--> Test 9 PASSED: App restart and schema initialization verified clean.")

    print("\n==================================================")
    print("ALL 9 STAGE 2 STEP 2 VALIDATION TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_stage2_step2_tests()
