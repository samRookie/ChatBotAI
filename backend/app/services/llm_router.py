"""Pass-through LLM router backed by the Gemini API.

For Stage 1 (v1) this router simply forwards the conversation history to a
Gemini model and returns the generated text. No retrieval or RAG logic lives
here.
"""

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import settings
from app.services import retrieval_service
from app.services.resilience import (
    build_retry_decorator,
    is_failover_eligible,
)

logger = logging.getLogger(__name__)

MODEL = settings.gemini_model
FALLBACK_MODEL = settings.gemini_fallback_model

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


def _sanitize_history(messages: list[dict]) -> list[dict]:
    """Map DB messages to Gemini contents with strictly alternating roles.

    Consecutive same-role messages are merged into a single message and any
    leading non-user messages are dropped so the array always starts with a
    'user' turn, satisfying Gemini's alternation requirement.
    """
    contents: list[dict] = []
    for message in messages:
        role = _ROLE_MAP.get(message.get("role", "user"), "user")
        text = message.get("content", "")
        if not text:
            continue
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += f"\n{text}"
        else:
            contents.append({"role": role, "parts": [{"text": text}]})

    while contents and contents[0]["role"] != "user":
        contents.pop(0)

    return contents


@build_retry_decorator(operation="chat", model_name=MODEL)
def _generate_primary(contents: list[dict], system_instruction: str | None = None) -> str:
    """Call primary Gemini model with bounded jittered exponential retry."""
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    config = (
        types.GenerateContentConfig(system_instruction=system_instruction)
        if system_instruction
        else None
    )
    response = client.models.generate_content(
        model=MODEL, contents=contents, config=config
    )
    return response.text


def _generate_fallback(contents: list[dict], system_instruction: str | None = None) -> str:
    """Execute a single one-shot fallback chat attempt against the verified alternate model."""
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    logger.info("Executing single fallback chat request to model=%s", FALLBACK_MODEL)
    config = (
        types.GenerateContentConfig(system_instruction=system_instruction)
        if system_instruction
        else None
    )
    response = client.models.generate_content(
        model=FALLBACK_MODEL, contents=contents, config=config
    )
    return response.text


def _generate(contents: list[dict], system_instruction: str | None = None) -> str:
    """Generate AI response with bounded retries and single-attempt failover on capacity exhaustion."""
    try:
        return _generate_primary(contents, system_instruction=system_instruction)
    except Exception as exc:
        if is_failover_eligible(exc):
            logger.warning(
                "Primary model %s exhausted with eligible error (%s). Attempting single fallback to %s.",
                MODEL,
                getattr(exc, "code", type(exc).__name__),
                FALLBACK_MODEL,
            )
            try:
                return _generate_fallback(contents, system_instruction=system_instruction)
            except Exception as fb_exc:
                logger.error(
                    "Fallback model %s failed: %s",
                    FALLBACK_MODEL,
                    fb_exc,
                    exc_info=True,
                )
                raise fb_exc from exc
        raise exc


def get_ai_response(
    mode: str,
    messages: list[dict],
    query_text: str | None = None,
) -> str:
    """Route the conversation history to the appropriate LLM behavior with silent RAG context."""
    if mode == "project_plan":
        # TODO(Stage 3): add project-planning behavior.
        pass

    if mode != "general":
        raise ValueError(f"Unsupported mode: {mode}")

    # Extract user query from messages if not provided explicitly
    if not query_text:
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                query_text = msg["content"]
                break

    # Fault-isolated retrieval of relevant memory chunks
    system_instruction: str | None = None
    if query_text:
        try:
            memories = retrieval_service.retrieve_relevant_memories(query_text)
            system_instruction = retrieval_service.format_retrieved_context(memories)
        except Exception as exc:
            logger.warning("Retrieval failed silently in router: %s", exc)
            system_instruction = None

    try:
        return _generate(_sanitize_history(messages), system_instruction=system_instruction)
    except genai_errors.APIError as exc:
        logger.error(f"LLM Error: {exc}", exc_info=True)
        raise
    except RuntimeError as exc:
        logger.error(f"LLM Error: {exc}", exc_info=True)
        raise


def generate_conversation_title(messages: list[dict]) -> str | None:
    """Analyze the conversation messages and generate a concise 2-5 word topic title."""
    if not messages:
        return "New Conversation"

    # Check for simple greeting-only conversation
    non_empty = [m for m in messages if m.get("content", "").strip()]
    if not non_empty:
        return "New Conversation"

    user_texts = [
        "".join(ch for ch in m["content"].strip().lower() if ch.isalnum() or ch.isspace()).strip()
        for m in non_empty
        if m.get("role") == "user"
    ]
    greetings = {
        "hi",
        "hello",
        "hey",
        "hola",
        "sup",
        "yo",
        "good morning",
        "good evening",
        "good afternoon",
        "greetings",
        "howdy",
        "hello good morning",
        "hi there",
        "hello there",
    }
    if len(user_texts) == 1 and user_texts[0] in greetings:
        return "New Conversation"

    conversation_snippet = "\n".join(
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
        for m in non_empty[-6:]
    )
    prompt_content = (
        f"Conversation:\n{conversation_snippet}\n\n"
        "Generate a concise, human-readable title of 2 to 5 words summarizing the core technical topic or user goal of this conversation. "
        "Do NOT use quotation marks, markdown formatting, trailing periods, or generic prefixes like 'Chat about' or 'Discussion'. "
        "Return ONLY the concise title text."
    )

    try:
        raw_title = _generate([{"role": "user", "parts": [{"text": prompt_content}]}])
        if not raw_title:
            return None

        clean_title = raw_title.strip().strip("\"'").strip()
        if clean_title.lower().startswith("title:"):
            clean_title = clean_title[6:].strip()

        # Enforce reasonable length constraint
        if len(clean_title) > 40:
            clean_title = clean_title[:37].rstrip() + "..."

        return clean_title if clean_title else None
    except Exception as exc:
        logger.warning("Failed to generate conversation topic title: %s", exc)
        return None

