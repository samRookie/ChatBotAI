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
    suggested_title: str | None = None


class TitleResponse(BaseModel):
    conversation_id: str
    title: str


class DbCheckResponse(BaseModel):
    sqlite_vec_version: str


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    updated_at: str


class ProjectDetailResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    updated_at: str
    conversation_count: int
    conversation_ids: list[str]


class ProjectDeleteResponse(BaseModel):
    id: str
    status: str = "deleted"


