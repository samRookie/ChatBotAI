import logging
import sqlite3

from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.api.models import ChatMessageRequest, ChatMessageResponse, MessageItem
from app.services import chat_service
from app.services.llm_router import get_ai_response

router = APIRouter()


@router.get("/{conversation_id}", response_model=list[MessageItem])
def get_messages(conversation_id: str) -> list[MessageItem]:
    return chat_service.get_conversation_history(conversation_id)


@router.post("/", response_model=ChatMessageResponse)
def chat(payload: ChatMessageRequest) -> ChatMessageResponse:
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
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500, detail="Failed to persist chat message"
        ) from exc
    except genai_errors.APIError as exc:
        chat_service.delete_message(user_message["id"])
        logging.error(f"LLM Error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable. Please try again.",
        ) from exc
    except RuntimeError as exc:
        chat_service.delete_message(user_message["id"])
        logging.error(f"LLM Error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="The AI service is not configured."
        ) from exc

    return ChatMessageResponse(
        conversation_id=conversation_id,
        message=MessageItem(**assistant_message),
    )
