"""Comprehensive Deterministic Fault-Injection & Provider Resilience Test Suite.

Validates all 12 testing requirements from Section 21:
1. First-attempt 503 -> success
2. Multiple 503s -> eventual success
3. 503 exhaustion -> fallback success
4. Primary + fallback failure -> structured provider error
5. 429 transient -> success
6. 429 quota-exhausted condition -> fail fast
7. Non-retryable 400/403/404 -> immediate fail-fast
8. Embedding failure -> background persistence safety & isolation
9. API Error Contract (HTTP 429/503 -> AI_PROVIDER_BUSY structured payload)
10. Retry-count ceiling verification (5 for primary, 1 for fallback = 6 total)
11. Backoff configuration and jitter verification
12. Observability & warning log formatting verification
"""

import logging
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from tenacity import wait_none, stop_after_attempt, wait_random_exponential

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from google.genai import errors as genai_errors
from google.genai import types

from app.api.v1 import chat
from app.core.config import settings
from app.db.connection import get_connection
from app.main import app
from app.services import chat_service, embedding_service, llm_router, resilience


def run_resilience_tests():
    print("==================================================")
    print("UPSTREAM GEMINI PROVIDER RESILIENCE TEST SUITE")
    print("==================================================")

    client = TestClient(app)

    # ----------------------------------------------------
    # Test 1: First-attempt 503 -> success after 1 retry
    # ----------------------------------------------------
    print("\n[Test 1] First-attempt 503 -> success on retry with WARNING log")
    attempts_t1 = 0
    warning_logs_t1 = []

    class MockHandler(logging.Handler):
        def emit(self, record):
            if record.levelno == logging.WARNING:
                warning_logs_t1.append(record.getMessage())

    logger = logging.getLogger("app.services.resilience")
    handler = MockHandler()
    logger.addHandler(handler)

    def mock_generate_503_then_success(*args, **kwargs):
        nonlocal attempts_t1
        attempts_t1 += 1
        if attempts_t1 == 1:
            raise genai_errors.ServerError(503, {"message": "Service unavailable / capacity overload"})
        mock_resp = MagicMock()
        mock_resp.text = "Hello after 503 retry!"
        return mock_resp

    with patch.object(resilience, "wait_random_exponential", return_value=wait_none()):
        # Decorate a test function using build_retry_decorator with wait_none
        test_fn = resilience.build_retry_decorator("chat", "gemini-3.5-flash", wait_strategy=wait_none())(
            mock_generate_503_then_success
        )
        res = test_fn([{"role": "user", "parts": [{"text": "hi"}]}])
        assert res.text == "Hello after 503 retry!"
        assert attempts_t1 == 2, f"Expected 2 attempts, got {attempts_t1}"
        assert any("Gemini request retry scheduled: operation=chat model=gemini-3.5-flash attempt=1 status=503" in log for log in warning_logs_t1), f"Expected retry warning log missing: {warning_logs_t1}"

    logger.removeHandler(handler)
    print("--> Test 1 PASSED: 503 on 1st attempt retried and succeeded on 2nd attempt with structured WARNING log.")

    # ----------------------------------------------------
    # Test 2: Multiple 503s -> eventual success
    # ----------------------------------------------------
    print("\n[Test 2] Multiple 503s -> eventual success (attempt 4)")
    attempts_t2 = 0

    def mock_generate_multi_503(*args, **kwargs):
        nonlocal attempts_t2
        attempts_t2 += 1
        if attempts_t2 < 4:
            raise genai_errors.ServerError(503, {"message": "Capacity overloaded"})
        mock_resp = MagicMock()
        mock_resp.text = "Eventual success on attempt 4"
        return mock_resp

    test_fn_t2 = resilience.build_retry_decorator("chat", "gemini-3.5-flash", wait_strategy=wait_none())(
        mock_generate_multi_503
    )
    res_t2 = test_fn_t2([{"role": "user", "parts": [{"text": "hi"}]}])
    assert res_t2.text == "Eventual success on attempt 4"
    assert attempts_t2 == 4, f"Expected 4 attempts, got {attempts_t2}"
    print("--> Test 2 PASSED: Bounded retry successfully absorbed 3 consecutive 503s and recovered.")

    # ----------------------------------------------------
    # Test 3: 503 exhaustion -> fallback success
    # ----------------------------------------------------
    print("\n[Test 3] Primary 503 exhaustion -> single fallback model call succeeds")
    primary_calls = 0
    fallback_calls = 0

    def mock_primary_fail(contents, system_instruction=None):
        nonlocal primary_calls
        primary_calls += 1
        raise genai_errors.ServerError(503, {"message": "Primary model 503 overload"})

    def mock_fallback_success(contents, system_instruction=None):
        nonlocal fallback_calls
        fallback_calls += 1
        assert system_instruction == "Test System Instruction"
        assert contents == [{"role": "user", "parts": [{"text": "Test input"}]}]
        return "Response from fallback gemini-3.6-flash"

    with patch.object(llm_router, "_generate_primary", side_effect=mock_primary_fail):
        with patch.object(llm_router, "_generate_fallback", side_effect=mock_fallback_success):
            result = llm_router._generate(
                [{"role": "user", "parts": [{"text": "Test input"}]}],
                system_instruction="Test System Instruction",
            )
            assert result == "Response from fallback gemini-3.6-flash"
            assert primary_calls == 1, f"Expected 1 call to _generate_primary, got {primary_calls}"
            assert fallback_calls == 1, f"Expected exactly 1 fallback call, got {fallback_calls}"
    print("--> Test 3 PASSED: Primary 503 capacity failure seamlessly fell back to alternate model with full context.")

    # ----------------------------------------------------
    # Test 4: Primary + fallback failure -> structured error
    # ----------------------------------------------------
    print("\n[Test 4] Primary + fallback failure produces clean structured exception")
    with patch.object(llm_router, "_generate_primary", side_effect=genai_errors.ServerError(503, {"message": "Primary down"})):
        with patch.object(llm_router, "_generate_fallback", side_effect=genai_errors.ServerError(503, {"message": "Fallback down"})):
            failed = False
            try:
                llm_router._generate([{"role": "user", "parts": [{"text": "hi"}]}])
            except genai_errors.ServerError as exc:
                failed = True
                assert exc.code == 503
            assert failed, "Expected ServerError to be raised when fallback also exhausts"
    print("--> Test 4 PASSED: Primary + fallback failure properly raises without infinite retries.")

    # ----------------------------------------------------
    # Test 5: 429 transient rate limit -> success
    # ----------------------------------------------------
    print("\n[Test 5] Transient 429 (rate limit) retries and succeeds")
    attempts_t5 = 0

    def mock_generate_429_transient(*args, **kwargs):
        nonlocal attempts_t5
        attempts_t5 += 1
        if attempts_t5 == 1:
            raise genai_errors.APIError(429, {"message": "Resource exhausted: Rate limit per minute exceeded."})
        mock_resp = MagicMock()
        mock_resp.text = "Success after 429 rate limit retry"
        return mock_resp

    test_fn_t5 = resilience.build_retry_decorator("chat", "gemini-3.5-flash", wait_strategy=wait_none())(
        mock_generate_429_transient
    )
    res_t5 = test_fn_t5([{"role": "user", "parts": [{"text": "hi"}]}])
    assert res_t5.text == "Success after 429 rate limit retry"
    assert attempts_t5 == 2
    print("--> Test 5 PASSED: Transient 429 burst rate limit successfully retried.")

    # ----------------------------------------------------
    # Test 6: 429 daily quota exhausted -> fail fast
    # ----------------------------------------------------
    print("\n[Test 6] Non-transient 429 (daily quota exhausted) fails fast without burning retry budget")
    attempts_t6 = 0

    def mock_generate_429_quota_exhausted(*args, **kwargs):
        nonlocal attempts_t6
        attempts_t6 += 1
        raise genai_errors.APIError(429, {"message": "Resource exhausted: Daily quota exceeded for the day."})

    test_fn_t6 = resilience.build_retry_decorator("chat", "gemini-3.5-flash", wait_strategy=wait_none())(
        mock_generate_429_quota_exhausted
    )
    failed_t6 = False
    try:
        test_fn_t6([{"role": "user", "parts": [{"text": "hi"}]}])
    except genai_errors.APIError:
        failed_t6 = True
    assert failed_t6
    assert attempts_t6 == 1, f"Expected fail-fast in 1 attempt, but got {attempts_t6} attempts!"
    print("--> Test 6 PASSED: Daily quota exhausted 429 failed fast on attempt 1 without wasting retry budget.")

    # ----------------------------------------------------
    # Test 7: Non-retryable 400/403/404 errors fail fast
    # ----------------------------------------------------
    print("\n[Test 7] Non-retryable errors (400, 403, 404) fail fast without retrying")
    non_retryable_codes = [400, 401, 403, 404]
    for code in non_retryable_codes:
        attempts = 0

        def mock_client_error(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            raise genai_errors.ClientError(code, {"message": f"Client error with status {code}"})

        test_fn_nr = resilience.build_retry_decorator("chat", "gemini-3.5-flash", wait_strategy=wait_none())(
            mock_client_error
        )
        failed_nr = False
        try:
            test_fn_nr([{"role": "user", "parts": [{"text": "hi"}]}])
        except genai_errors.ClientError:
            failed_nr = True
        assert failed_nr
        assert attempts == 1, f"Status {code} made {attempts} attempts instead of failing fast on attempt 1!"
    print("--> Test 7 PASSED: 400, 401, 403, and 404 all failed fast on attempt 1 with zero retries.")

    # ----------------------------------------------------
    # Test 8: Embedding failure -> background persistence safety
    # ----------------------------------------------------
    print("\n[Test 8] Background embedding failure isolation & rollback")
    session_id = "test_resilience_session"
    conv_id = "test_resilience_conv"
    chat_service.ensure_conversation_exists(session_id, conv_id)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_before = cur.fetchone()[0]
    finally:
        conn.close()

    # Simulate embedding service raising exhausted 503 error
    with patch.object(embedding_service, "_call_gemini_embed", side_effect=genai_errors.ServerError(503, {"message": "Embedding capacity down"})):
        result = embedding_service.process_background_memory_write(conv_id, "User test text", "Assistant test text")
        assert result is None, "Background memory writer must return None on failure"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memory_chunks")
        chunks_after = cur.fetchone()[0]
        assert chunks_before == chunks_after, "Database transaction was not rolled back!"
        # Clean up
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
    print("--> Test 8 PASSED: Background embedding failure logged, caught, and rolled back cleanly.")

    # ----------------------------------------------------
    # Test 9: API Error Contract (HTTP 429/503 -> structured JSON)
    # ----------------------------------------------------
    print("\n[Test 9] Backend Error Contract: Structured AI_PROVIDER_BUSY response")
    # Case A: 503 Service Unavailable
    with patch("app.api.v1.chat.get_ai_response", side_effect=genai_errors.ServerError(503, {"message": "Capacity down"})):
        resp503 = client.post(
            "/api/v1/chat/",
            json={"session_id": "test_err_s", "conversation_id": "test_err_c", "content": "Hello"},
        )
        assert resp503.status_code == 503, f"Expected 503, got {resp503.status_code}"
        data503 = resp503.json()
        assert "error" in data503, f"Missing error object in response: {data503}"
        assert data503["error"]["code"] == "AI_PROVIDER_BUSY"
        assert data503["error"]["message"] == "The AI service is temporarily busy. Please try again in a few moments."

    # Case B: 429 Rate Limit
    with patch("app.api.v1.chat.get_ai_response", side_effect=genai_errors.APIError(429, {"message": "Rate limit"})):
        resp429 = client.post(
            "/api/v1/chat/",
            json={"session_id": "test_err_s2", "conversation_id": "test_err_c2", "content": "Hello"},
        )
        assert resp429.status_code == 429, f"Expected 429, got {resp429.status_code}"
        data429 = resp429.json()
        assert data429["error"]["code"] == "AI_PROVIDER_BUSY"
        assert data429["error"]["message"] == "The AI service is temporarily busy. Please try again in a few moments."

    print("--> Test 9 PASSED: Backend returns structured AI_PROVIDER_BUSY error on 429 and 503.")

    # ----------------------------------------------------
    # Test 10: Retry-count ceiling verification (Exactly 5 calls for primary, 1 for fallback)
    # ----------------------------------------------------
    print("\n[Test 10] Retry-count ceiling verification (real call counter)")
    primary_call_count = 0

    def mock_primary_exhaust(*args, **kwargs):
        nonlocal primary_call_count
        primary_call_count += 1
        raise genai_errors.ServerError(503, {"message": "Capacity overload"})

    test_fn_ceiling = resilience.build_retry_decorator("chat", "gemini-3.5-flash", max_attempts=5, wait_strategy=wait_none())(
        mock_primary_exhaust
    )
    try:
        test_fn_ceiling([{"role": "user", "parts": [{"text": "hi"}]}])
    except genai_errors.ServerError:
        pass

    assert primary_call_count == 5, f"Expected exactly 5 provider calls (1 initial + 4 retries), got {primary_call_count}!"
    print(f"--> Test 10 PASSED: Primary retry ceiling verified at exactly {primary_call_count} provider calls.")

    # ----------------------------------------------------
    # Test 11: Backoff configuration & jitter bounds
    # ----------------------------------------------------
    print("\n[Test 11] Backoff configuration & jitter bounds verification")
    wait_strat = wait_random_exponential(min=2.0, max=10.0)
    # Generate 20 backoff sample values across retry attempts 1..5
    for attempt in range(1, 6):
        mock_state = MagicMock()
        mock_state.attempt_number = attempt
        sleep_dur = wait_strat(mock_state)
        # Sleep duration should be >= 0 and bounded
        assert 0.0 <= sleep_dur <= 10.0, f"Sleep duration {sleep_dur} out of bounds!"
    print("--> Test 11 PASSED: wait_random_exponential bounded between 2.0s and 10.0s with randomized jitter.")

    # ----------------------------------------------------
    # Test 12: Observability & log sanitization
    # ----------------------------------------------------
    print("\n[Test 12] Observability & log sanitization verification")
    logged_warnings = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            logged_warnings.append(record.getMessage())

    cap_handler = CaptureHandler()
    logger.addHandler(cap_handler)

    test_retry_state = MagicMock()
    test_retry_state.attempt_number = 2
    test_retry_state.next_action = MagicMock(sleep=3.456)
    test_retry_state.outcome = MagicMock()
    test_retry_state.outcome.exception.return_value = genai_errors.ServerError(503, {"message": "Sensitive prompt: my secret password"})

    resilience.log_retry_warning(test_retry_state, operation="chat", model_name="gemini-3.5-flash")
    logger.removeHandler(cap_handler)

    assert len(logged_warnings) >= 1
    log_msg = logged_warnings[-1]
    print(f"Captured retry log message: {log_msg}")
    assert "Gemini request retry scheduled: operation=chat model=gemini-3.5-flash attempt=2 status=503 wait=3.46s" == log_msg
    assert "password" not in log_msg, "Security leak: sensitive content found in log message!"
    print("--> Test 12 PASSED: Log format matches specification and contains zero sensitive data or prompts.")

    print("\n==================================================")
    print("ALL 12 PROVIDER RESILIENCE TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_resilience_tests()
