import logging
import sqlite3

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors

from app.api.models import (
    ChatMessageRequest,
    ChatMessageResponse,
    MessageItem,
    TitleResponse,
)
from app.services import chat_service, embedding_service
from app.services.llm_router import generate_conversation_title, get_ai_response

router = APIRouter()


@router.get("/{conversation_id}", response_model=list[MessageItem])
def get_messages(conversation_id: str) -> list[MessageItem]:
    return chat_service.get_conversation_history(conversation_id)


@router.post("/{conversation_id}/title", response_model=TitleResponse)
def get_title(conversation_id: str) -> TitleResponse:
    history = chat_service.get_conversation_history(conversation_id)
    title = generate_conversation_title(history) or "New Conversation"
    return TitleResponse(conversation_id=conversation_id, title=title)


@router.post("/", response_model=ChatMessageResponse)
def chat(
    payload: ChatMessageRequest,
    background_tasks: BackgroundTasks,
):
    user_message = None
    try:
        conversation_id = chat_service.ensure_conversation_exists(
            payload.session_id, payload.conversation_id
        )

        user_message = chat_service.save_message(
            conversation_id, "user", payload.content
        )

        history = chat_service.get_conversation_history(conversation_id)

        reply = get_ai_response(mode="general", messages=history)

        assistant_message = chat_service.save_message(
            conversation_id, "assistant", reply
        )

        # Schedule asynchronous post-response background memory persistence
        background_tasks.add_task(
            embedding_service.process_background_memory_write,
            conversation_id,
            payload.content,
            reply,
        )
    except sqlite3.Error as exc:
        logging.error("Database error during chat: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to persist chat message.",
                }
            },
        )
    except genai_errors.APIError as exc:
        if user_message:
            chat_service.delete_message(user_message["id"])
        logging.error("LLM Provider API Error: %s", exc, exc_info=False)
        status_code = 429 if getattr(exc, "code", None) == 429 else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "AI_PROVIDER_BUSY",
                    "message": "The AI service is temporarily busy. Please try again in a few moments.",
                }
            },
        )
    except RuntimeError as exc:
        if user_message:
            chat_service.delete_message(user_message["id"])
        logging.error("LLM Runtime Error: %s", exc, exc_info=False)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "AI_PROVIDER_CONFIG_ERROR",
                    "message": "The AI service is not configured.",
                }
            },
        )
    except Exception as exc:
        if user_message:
            chat_service.delete_message(user_message["id"])
        logging.error("Unexpected error in chat: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                }
            },
        )

    return ChatMessageResponse(
        conversation_id=conversation_id,
        message=MessageItem(**assistant_message),
    )

