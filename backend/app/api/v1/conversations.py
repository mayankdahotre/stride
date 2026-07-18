import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.graph.runtime import graph_runtime
from app.repositories.conversations import ConversationRepository
from app.repositories.products import ProductRepository
from app.schemas.conversations import (
    ConversationResponse,
    CreateConversationResponse,
    SendMessageRequest,
)
from app.schemas.shopping import ProductResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


def sse(event: str, data: dict[str, object]) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, default=str, separators=(',', ':'))}\n\n"
    )


def envelope_events(envelope: dict[str, object]) -> list[str]:
    chunks: list[str] = []
    products = envelope.get("products")
    if products is not None:
        chunks.append(sse("products", {"products": products}))
    for event in ("comparison", "recommendation", "plan"):
        value = envelope.get(event)
        if value is not None:
            chunks.append(sse(event, {event: value}))
    return chunks


def _token_or_401(value: str | None) -> str:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Conversation-Token header is required",
        )
    return value


@router.post("", response_model=CreateConversationResponse, status_code=201)
async def create_conversation(
    db: Annotated[Session, Depends(get_db)],
) -> CreateConversationResponse:
    thread, token = await asyncio.to_thread(ConversationRepository(db).create)
    return CreateConversationResponse(
        thread_id=thread.id,
        conversation_token=token,
        title=thread.title,
        created_at=thread.created_at,
    )


@router.get("/{thread_id}", response_model=ConversationResponse)
async def get_conversation(
    thread_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    conversation_token: Annotated[
        str | None, Header(alias="X-Conversation-Token")
    ] = None,
) -> ConversationResponse:
    repository = ConversationRepository(db)
    thread = await asyncio.to_thread(
        repository.get_authorized, thread_id, _token_or_401(conversation_token)
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    payload = await asyncio.to_thread(repository.serialize, thread)
    return ConversationResponse.model_validate(payload)


@router.post("/{thread_id}/messages/stream")
async def stream_message(
    thread_id: UUID,
    body: SendMessageRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    conversation_token: Annotated[
        str | None, Header(alias="X-Conversation-Token")
    ] = None,
) -> StreamingResponse:
    repository = ConversationRepository(db)
    token = _token_or_401(conversation_token)
    thread = await asyncio.to_thread(repository.get_authorized, thread_id, token)
    if thread is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def events() -> AsyncIterator[str]:
        try:
            yield sse(
                "metadata",
                {"thread_id": str(thread_id), "request_id": str(body.request_id)},
            )
            cached = await asyncio.to_thread(
                repository.get_cached, thread_id, body.request_id
            )
            if cached is not None:
                yield sse("status", {"stage": "idempotent_replay"})
                for chunk in envelope_events(cached):
                    yield chunk
                yield sse("done", cached)
                return

            yield sse("status", {"stage": "retrieving_products"})
            products, source = await asyncio.to_thread(
                ProductRepository(db).search_candidates, body.content
            )
            candidates = [
                ProductResponse.model_validate(product).model_dump(mode="json")
                for product in products
            ]
            if await request.is_disconnected():
                return

            yield sse("status", {"stage": "running_graph"})
            result = await graph_runtime.graph.ainvoke(
                {
                    "content": body.content,
                    "explicit_intent": body.intent,
                    "candidates": candidates,
                },
                config={
                    "configurable": {
                        "thread_id": str(thread_id),
                        "checkpoint_ns": "commerce",
                    }
                },
            )
            intent = result["intent"]
            envelope: dict[str, object] = {
                "message": {
                    "role": "assistant",
                    "content": result["content_out"],
                    "intent": intent,
                },
                "intent": intent,
                "products": result.get("products", []),
                "comparison": result.get("comparison"),
                "recommendation": result.get("recommendation"),
                "plan": result.get("plan"),
                "clarification": result.get("clarification", False),
                "model_source": result.get("model_source", "fallback"),
                "catalog_source": source,
            }
            if await request.is_disconnected():
                return

            saved = await asyncio.to_thread(
                repository.save_exchange,
                thread_id,
                body.request_id,
                body.content,
                intent,
                envelope,
            )
            for chunk in envelope_events(saved):
                yield chunk
            for token_part in str(saved["message"]["content"]).split():  # type: ignore[index]
                if await request.is_disconnected():
                    return
                yield sse("token", {"token": f"{token_part} "})
            yield sse("done", saved)
        except asyncio.CancelledError:
            return
        except Exception:
            yield sse(
                "error",
                {
                    "code": "processing_error",
                    "message": "Unable to process the message.",
                },
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
