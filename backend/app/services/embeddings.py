import asyncio
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Lazily load an optional local model; never download during a request."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._load_attempted = False

    def _load_model(self) -> Any | None:
        if self._load_attempted or not settings.embeddings_enabled:
            return self._model
        self._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                settings.embedding_model, local_files_only=True
            )
        except (ImportError, OSError, ValueError) as exc:
            logger.info("Embedding model unavailable; vector search disabled: %s", exc)
        return self._model

    async def embed(self, text: str) -> list[float] | None:
        if not text.strip():
            return None

        def encode() -> list[float] | None:
            model = self._load_model()
            if model is None:
                return None
            vector = model.encode(text, normalize_embeddings=True)
            values = [float(value) for value in vector]
            if len(values) != settings.embedding_dimension:
                logger.warning("Unexpected embedding dimension; vector search disabled")
                return None
            return values

        try:
            return await asyncio.to_thread(encode)
        except Exception as exc:  # Third-party backends can raise many exception types.
            logger.warning("Embedding failed; vector search disabled: %s", exc)
            return None


embedding_service = EmbeddingService()
