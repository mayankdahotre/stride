import json
import logging
from typing import Literal, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)
Structured = TypeVar("Structured", bound=BaseModel)


class IntentDecision(BaseModel):
    intent: Literal["search", "compare", "recommend", "plan"]


class CommerceExtraction(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=20)
    product_ids: list[int] = Field(default_factory=list, max_length=20)
    sport: str | None = None
    budget: float | None = Field(default=None, ge=0)


class Explanation(BaseModel):
    explanation: str = Field(min_length=1, max_length=800)


class OllamaGateway:
    """The only Ollama boundary; every response is schema validated."""

    async def structured(
        self, schema: type[Structured], system: str, user: str
    ) -> Structured:
        if not settings.conversational_model_enabled:
            raise RuntimeError("Conversational model disabled")
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "format": schema.model_json_schema(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            response = await client.post(
                f"{settings.ollama_url.rstrip('/')}/api/chat", json=payload
            )
            response.raise_for_status()
        try:
            content = response.json()["message"]["content"]
            return schema.model_validate_json(content)
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            logger.info("Rejected malformed Ollama structured output: %s", exc)
            raise ValueError("Invalid structured model output") from exc


gateway = OllamaGateway()
