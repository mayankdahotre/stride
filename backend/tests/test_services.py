from decimal import Decimal

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.repositories.products import ProductRepository
from app.schemas.shopping import ParsedQuery
from app.services.embeddings import EmbeddingService
from app.services.query_parser import QueryParser

ORIGINAL_PARSE = QueryParser.parse


def test_deterministic_parser_handles_between_prices() -> None:
    parsed = QueryParser.parse_deterministically(
        "Show me an electronics keyboard between $50 and $90"
    )
    assert parsed.category == "Electronics"
    assert parsed.min_price == Decimal("50")
    assert parsed.max_price == Decimal("90")
    assert "keyboard" in parsed.keywords


@pytest.mark.asyncio
async def test_query_parser_recovers_when_ollama_is_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = QueryParser()

    async def offline(query: str) -> object:
        request = httpx.Request("POST", "http://localhost/api/chat")
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(parser, "_parse_with_ollama", offline)
    parsed, source = await ORIGINAL_PARSE(parser, "running shoes under $100")
    assert source == "fallback"
    assert parsed.category == "Footwear"
    assert parsed.max_price == Decimal("100")


@pytest.mark.asyncio
async def test_query_parser_keeps_deterministic_numeric_constraints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = QueryParser()

    async def inaccurate_ai(query: str) -> ParsedQuery:
        return ParsedQuery(category="Footwear", min_price=100, max_price=100)

    monkeypatch.setattr(parser, "_parse_with_ollama", inaccurate_ai)
    parsed, source = await ORIGINAL_PARSE(parser, "running shoes under 100")
    assert source == "ollama"
    assert parsed.min_price is None
    assert parsed.max_price == Decimal("100")
    assert "running" in parsed.keywords


@pytest.mark.asyncio
async def test_query_parser_discards_unknown_ai_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = QueryParser()

    async def hallucinated_category(query: str) -> ParsedQuery:
        return ParsedQuery(category="Sports")

    monkeypatch.setattr(parser, "_parse_with_ollama", hallucinated_category)
    parsed, source = await ORIGINAL_PARSE(parser, "hydration for a long hike")
    assert source == "ollama"
    assert parsed.category is None


@pytest.mark.asyncio
async def test_embeddings_are_a_noop_when_disabled() -> None:
    assert await EmbeddingService().embed("running shoes") is None


def test_repository_applies_keyword_category_and_price_filters() -> None:
    products, source = ProductRepository(None).search(
        keywords=["wireless"],
        category="electronics",
        min_price=Decimal("50"),
        max_price=Decimal("100"),
        limit=5,
    )
    assert source == "fallback"
    assert [product.name for product in products] == ["QuietKeys Wireless Keyboard"]


def test_repository_recovers_from_database_failure() -> None:
    class BrokenSession:
        rolled_back = False

        def scalars(self, statement: object) -> object:
            raise OperationalError("select", {}, RuntimeError("offline"))

        def rollback(self) -> None:
            self.rolled_back = True

    session = BrokenSession()
    products, source = ProductRepository(session).search(  # type: ignore[arg-type]
        keywords=["hoodie"],
        category=None,
        min_price=None,
        max_price=None,
        limit=10,
    )
    assert source == "fallback"
    assert session.rolled_back is True
    assert products[0].name == "CloudSoft Hoodie"


def test_settings_parse_comma_separated_origins() -> None:
    configured = Settings(
        _env_file=None,
        cors_origins="https://shop.example, https://admin.example",  # type: ignore[arg-type]
    )
    assert configured.cors_origins == [
        "https://shop.example",
        "https://admin.example",
    ]


def test_settings_reject_wildcard_cors() -> None:
    try:
        Settings(_env_file=None, cors_origins=["*"])
    except ValueError as exc:
        assert "explicit origins" in str(exc)
    else:
        raise AssertionError("Wildcard CORS must be rejected")


def test_database_url_escapes_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    configured = Settings(
        _env_file=None,
        postgres_user="stride@example",
        postgres_password="p@ss word",
    )
    assert "stride%40example:p%40ss+word@" in configured.sqlalchemy_database_url
