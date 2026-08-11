from datetime import datetime

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    session_id: str
    conversation_id: str
    content: str


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatMessageResponse(BaseModel):
    conversation_id: str
    message: MessageItem
