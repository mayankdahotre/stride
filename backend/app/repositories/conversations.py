import hashlib
import hmac
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conversation import ConversationMessage, ConversationThread


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class MemoryMessage:
    id: uuid.UUID
    request_id: uuid.UUID | None
    role: str
    content: str
    intent: str | None
    envelope: dict[str, object] | None
    created_at: datetime


@dataclass
class MemoryThread:
    id: uuid.UUID
    token_hash: str
    title: str
    created_at: datetime
    messages: list[MemoryMessage] = field(default_factory=list)


_memory_threads: dict[uuid.UUID, MemoryThread] = {}
_memory_lock = threading.RLock()


class ConversationRepository:
    """Postgres persistence with a process-local fallback for offline operation."""

    def __init__(self, session: Session | None) -> None:
        self.session = session

    def create(self, title: str = "New conversation") -> tuple[object, str]:
        token = secrets.token_urlsafe(32)
        if self.session is not None:
            try:
                thread = ConversationThread(token_hash=hash_token(token), title=title)
                self.session.add(thread)
                self.session.commit()
                self.session.refresh(thread)
                return thread, token
            except SQLAlchemyError:
                self.session.rollback()
        thread = MemoryThread(
            id=uuid.uuid4(),
            token_hash=hash_token(token),
            title=title,
            created_at=datetime.now(UTC),
        )
        with _memory_lock:
            _memory_threads[thread.id] = thread
        return thread, token

    def get_authorized(self, thread_id: uuid.UUID, token: str) -> object | None:
        thread = self._get(thread_id)
        if thread is None:
            return None
        return thread if hmac.compare_digest(thread.token_hash, hash_token(token)) else None

    def get_cached(
        self, thread_id: uuid.UUID, request_id: uuid.UUID
    ) -> dict[str, object] | None:
        thread = self._get(thread_id)
        if thread is None:
            return None
        messages = self._messages(thread)
        for message in messages:
            if (
                message.role == "assistant"
                and message.request_id == request_id
                and message.envelope is not None
            ):
                return message.envelope
        return None

    def save_exchange(
        self,
        thread_id: uuid.UUID,
        request_id: uuid.UUID,
        user_content: str,
        intent: str,
        envelope: dict[str, object],
    ) -> dict[str, object]:
        cached = self.get_cached(thread_id, request_id)
        if cached is not None:
            return cached
        assistant_content = str(envelope["message"]["content"])  # type: ignore[index]
        if self.session is not None:
            try:
                self.session.add_all(
                    [
                        ConversationMessage(
                            thread_id=thread_id,
                            request_id=None,
                            role="user",
                            content=user_content,
                            intent=intent,
                        ),
                        ConversationMessage(
                            thread_id=thread_id,
                            request_id=request_id,
                            role="assistant",
                            content=assistant_content,
                            intent=intent,
                            envelope=envelope,
                        ),
                    ]
                )
                self.session.commit()
                return envelope
            except SQLAlchemyError:
                self.session.rollback()
                cached = self.get_cached(thread_id, request_id)
                if cached is not None:
                    return cached
                raise
        with _memory_lock:
            thread = _memory_threads[thread_id]
            now = datetime.now(UTC)
            thread.messages.extend(
                [
                    MemoryMessage(
                        uuid.uuid4(), None, "user", user_content, intent, None, now
                    ),
                    MemoryMessage(
                        uuid.uuid4(),
                        request_id,
                        "assistant",
                        assistant_content,
                        intent,
                        envelope,
                        now,
                    ),
                ]
            )
        return envelope

    def serialize(self, thread: object) -> dict[str, object]:
        return {
            "thread_id": thread.id,
            "title": thread.title,
            "created_at": thread.created_at,
            "messages": [
                {
                    "id": item.id,
                    "request_id": item.request_id,
                    "role": item.role,
                    "content": item.content,
                    "intent": item.intent,
                    "envelope": item.envelope,
                    "created_at": item.created_at,
                }
                for item in self._messages(thread)
            ],
        }

    def _get(self, thread_id: uuid.UUID) -> object | None:
        if self.session is not None:
            try:
                return self.session.scalar(
                    select(ConversationThread).where(ConversationThread.id == thread_id)
                )
            except SQLAlchemyError:
                self.session.rollback()
        with _memory_lock:
            return _memory_threads.get(thread_id)

    def _messages(self, thread: object) -> list[object]:
        if isinstance(thread, MemoryThread):
            return list(thread.messages)
        if self.session is None:
            return []
        return list(
            self.session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.thread_id == thread.id)
                .order_by(ConversationMessage.created_at, ConversationMessage.id)
            ).all()
        )


def clear_memory_conversations() -> None:
    """Test helper; not used by application code."""
    with _memory_lock:
        _memory_threads.clear()
