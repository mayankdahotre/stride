from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Intent = Literal["search", "compare", "recommend", "plan"]


class CreateConversationResponse(BaseModel):
    thread_id: UUID
    conversation_token: str
    title: str
    created_at: datetime


class ConversationMessageResponse(BaseModel):
    id: UUID
    request_id: UUID | None
    role: Literal["user", "assistant"]
    content: str
    intent: Intent | None = None
    envelope: dict[str, object] | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    thread_id: UUID
    title: str
    created_at: datetime
    messages: list[ConversationMessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    request_id: UUID
    intent: Intent | None = None
