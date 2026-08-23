"""Embedding and memory writer service backed by the Gemini API and sqlite-vec.

This service converts raw conversational text chunks into 768-dimensional
Gemini embedding vectors and atomically persists them into `memory_chunks`
and `memory_vectors` with strict rowid correspondence.
"""

import logging
import sqlite3
from datetime import datetime, timezone

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
import sqlite_vec

from app.core.config import settings
from app.db.connection import get_connection
from app.services.resilience import build_retry_decorator

logger = logging.getLogger(__name__)

# Initialize the client securely from the configured API key. If no key is
# configured the client stays None so the app can still boot; calls will raise
# a clear error instead of failing at import time.
client = (
    genai.Client(api_key=settings.gemini_api_key)
    if settings.gemini_api_key
    else None
)


def _utc_now() -> str:
    """Return current UTC timestamp in ISO-8601 string format."""
    return datetime.now(timezone.utc).isoformat()


def validate_input_text(text: str) -> str:
    """Validate that input text is a non-empty string."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input text must be a non-empty string")
    return text.strip()


def validate_vector_dimension(
    embedding: list[float], expected_dim: int = settings.gemini_embedding_dim
) -> None:
    """Strictly validate that embedding is a list of floats of exact expected dimension."""
    if not isinstance(embedding, (list, tuple)):
        raise ValueError("Embedding must be a sequence of numerical values")
    if len(embedding) != expected_dim:
        raise ValueError(
            f"Invalid embedding dimension: expected {expected_dim}, got {len(embedding)}"
        )


@build_retry_decorator(
    operation="embedding", model_name=settings.gemini_embedding_model
)
def _call_gemini_embed(text: str) -> list[float]:
    """Call Gemini embedding endpoint with retry on rate limits and server errors."""
    if client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    config = types.EmbedContentConfig(
        output_dimensionality=settings.gemini_embedding_dim
    )
    response = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=text,
        config=config,
    )

    if not response.embeddings or not response.embeddings[0].values:
        raise ValueError("Empty or malformed embedding received from Gemini API")

    return list(response.embeddings[0].values)


def generate_embedding(text: str) -> list[float]:
    """Generate a 768-dimensional Gemini embedding vector for raw text."""
    valid_text = validate_input_text(text)
    try:
        raw_vector = _call_gemini_embed(valid_text)
    except genai_errors.APIError as exc:
        logger.error(
            "Gemini Embedding API Error: code=%s message=%s",
            getattr(exc, "code", "unknown"),
            getattr(exc, "message", str(exc)),
            exc_info=True,
        )
        raise
    except RuntimeError as exc:
        logger.error("Embedding runtime error: %s", exc, exc_info=True)
        raise

    validate_vector_dimension(raw_vector, settings.gemini_embedding_dim)
    return raw_vector


def store_embedding(
    conversation_id: str,
    chunk_text: str,
    embedding: list[float],
    project_id: str | None = None,
) -> int:
    """Atomically store a memory chunk and its corresponding vector in SQLite.

    Ensures that memory_chunks.id == memory_vectors.rowid.
    Inherits project_id from conversation if omitted, and validates ownership consistency.
    Rolls back completely if either insertion fails.
    """
    if not conversation_id or not str(conversation_id).strip():
        raise ValueError("conversation_id must be a non-empty string")
    valid_text = validate_input_text(chunk_text)
    validate_vector_dimension(embedding, settings.gemini_embedding_dim)

    serialized_vector = sqlite_vec.serialize_float32(embedding)
    now = _utc_now()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Verify conversation ownership and project inheritance
        cursor.execute(
            "SELECT project_id FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conv_row = cursor.fetchone()
        if conv_row is not None:
            conv_project_id = conv_row["project_id"]
            if project_id is not None and conv_project_id is not None and project_id != conv_project_id:
                raise ValueError(
                    f"Project ID mismatch: conversation '{conversation_id}' belongs to project '{conv_project_id}', but project_id '{project_id}' was provided"
                )
            if project_id is not None and conv_project_id is None:
                raise ValueError(
                    f"Project ID mismatch: conversation '{conversation_id}' is a general conversation, but project_id '{project_id}' was provided"
                )
            effective_project_id = conv_project_id if project_id is None else project_id
        else:
            effective_project_id = project_id

        # Insert metadata row
        cursor.execute(
            "INSERT INTO memory_chunks (conversation_id, project_id, chunk_text, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, effective_project_id, valid_text, now),
        )
        rowid = cursor.lastrowid
        if rowid is None:
            raise sqlite3.DatabaseError("Failed to retrieve rowid from memory_chunks insert")

        # Insert vector with matching rowid
        cursor.execute(
            "INSERT INTO memory_vectors (rowid, embedding) VALUES (?, ?)",
            (rowid, serialized_vector),
        )
        conn.commit()
        return rowid
    except Exception as exc:
        conn.rollback()
        logger.error(
            "Failed to persist memory chunk/vector for conversation_id=%s: %s",
            conversation_id,
            exc,
            exc_info=True,
        )
        raise
    finally:
        conn.close()


def store_memory(
    conversation_id: str,
    chunk_text: str,
    embedding: list[float] | None = None,
    project_id: str | None = None,
) -> int:
    """High-level pipeline: generate embedding (if not provided) and store atomically."""
    if embedding is None:
        embedding = generate_embedding(chunk_text)
    return store_embedding(
        conversation_id=conversation_id,
        chunk_text=chunk_text,
        embedding=embedding,
        project_id=project_id,
    )


def process_background_memory_write(
    conversation_id: str,
    user_text: str,
    assistant_text: str,
    project_id: str | None = None,
) -> int | None:
    """Asynchronously format, embed, and atomically persist an exchange as long-term memory.

    Accepts minimal immutable primitives to ensure safe background execution.
    Wrapped in complete fault isolation; all failures are logged at WARNING and never raise.
    """
    if not conversation_id or not user_text or not str(user_text).strip():
        return None

    try:
        # Build clean dialogue chunk
        chunk_text = f"User: {user_text.strip()}\nAssistant: {assistant_text.strip()}"
        rowid = store_memory(
            conversation_id=conversation_id,
            chunk_text=chunk_text,
            project_id=project_id,
        )
        logger.debug(
            "Background memory persisted successfully: rowid=%s conversation_id=%s project_id=%s",
            rowid,
            conversation_id,
            project_id,
        )
        return rowid
    except Exception as exc:
        logger.warning(
            "Background memory write failed for conversation_id=%s: %s: %s",
            conversation_id,
            type(exc).__name__,
            exc,
            exc_info=False,
        )
        return None


