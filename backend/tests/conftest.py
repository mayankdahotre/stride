from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.repositories.conversations import clear_memory_conversations
from app.services.query_parser import QueryParser


def no_database() -> Generator[None, None, None]:
    yield None


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    original_api_key = settings.api_key
    original_embeddings = settings.embeddings_enabled
    original_conversational_model = settings.conversational_model_enabled
    original_checkpointer = settings.langgraph_postgres_checkpointer
    settings.api_key = ""
    settings.embeddings_enabled = False
    settings.conversational_model_enabled = False
    settings.langgraph_postgres_checkpointer = False
    clear_memory_conversations()

    async def deterministic_parse(
        self: QueryParser, query: str
    ) -> tuple[object, str]:
        return self.parse_deterministically(query), "fallback"

    monkeypatch.setattr(QueryParser, "parse", deterministic_parse)
    app.dependency_overrides[get_db] = no_database
    yield
    app.dependency_overrides.clear()
    settings.api_key = original_api_key
    settings.embeddings_enabled = original_embeddings
    settings.conversational_model_enabled = original_conversational_model
    settings.langgraph_postgres_checkpointer = original_checkpointer


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
