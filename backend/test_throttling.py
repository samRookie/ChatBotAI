"""Centralized test throttling utility for live Gemini API test suites.

Enforces a configurable delay between consecutive live-provider calls
to prevent quota exhaustion or burst rate-limiting during test runs.
Has zero effect on unit/mocked tests.
"""

import os
import time

# Default spacing between live provider calls (seconds)
DEFAULT_LIVE_CALL_SPACING = float(os.getenv("TEST_LIVE_CALL_SPACING", "1.5"))

# Global toggle to disable throttling (e.g. in fully mocked test environments)
_THROTTLING_ENABLED = os.getenv("DISABLE_TEST_THROTTLING", "0") != "1"


def wait_between_live_api_calls(seconds: float = DEFAULT_LIVE_CALL_SPACING) -> None:
    """Pause execution between consecutive live API calls in test suites.

    Only applies if throttling is enabled and delay > 0.
    """
    if _THROTTLING_ENABLED and seconds > 0:
        time.sleep(seconds)


def set_test_throttling_enabled(enabled: bool) -> None:
    """Globally enable or disable live test call throttling."""
    global _THROTTLING_ENABLED
    _THROTTLING_ENABLED = enabled
