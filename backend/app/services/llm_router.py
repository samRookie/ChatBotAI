"""Pass-through LLM router backed by the Gemini API.

For Stage 1 (v1) this router simply forwards the conversation history to a
Gemini model and returns the generated text. No retrieval or RAG logic lives
here.
"""

from google import genai
from google.genai import errors as genai_errors
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

MODEL = settings.gemini_model

# Initialize the client securely from the configured API key. If no key is
# configured the client stays None so the app can still boot; calls will raise
# a clear error instead of failing at import time.
client = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)

_ROLE_MAP = {
    "user": "user",
    "assistant": "model",
}


def _format_contents(messages: list[dict]) -> list[dict]:
    """Map DB roles ('user'/'assistant') to Gemini roles ('user'/'model')."""
    contents = []
    for message in messages:
        role = _ROLE_MAP.get(message.get("role", "user"), "user")
        contents.append(
            {"role": role, "parts": [{"text": message.get("content", "")}]}
        )
    return contents


def _is_rate_limited(exc: BaseException) -> bool:
    """True only for 429 (Rate Limit / Resource Exhausted) API errors."""
    return isinstance(exc, genai_errors.APIError) and exc.code == 429


@retry(
    retry=retry_if_exception(_is_rate_limited),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _generate(contents: list[dict]) -> str:
    """Call the Gemini API, retrying on rate limits with exponential backoff."""
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    response = client.models.generate_content(model=MODEL, contents=contents)
    return response.text


def get_ai_response(mode: str, messages: list[dict]) -> str:
    """Route the conversation history to the appropriate LLM behavior."""
    if mode == "project_plan":
        # TODO(Stage 3): add project-planning behavior.
        pass

    if mode != "general":
        raise ValueError(f"Unsupported mode: {mode}")

    return _generate(_format_contents(messages))
