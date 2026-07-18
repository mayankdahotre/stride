from fastapi.testclient import TestClient

from app.core.config import settings


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Stride API"}


def test_categories_use_seeded_fallback(client: TestClient) -> None:
    response = client.get("/api/v1/products/categories")
    assert response.status_code == 200
    assert "Electronics" in response.json()["categories"]
    assert response.json()["categories"] == sorted(response.json()["categories"])


def test_parse_query_fallback_extracts_filters(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopping/parse-query",
        json={"query": "Find running shoes under $100"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["parsed"]["category"] == "Footwear"
    assert body["parsed"]["max_price"] == "100"
    assert "running" in body["parsed"]["keywords"]


def test_search_filters_seeded_products(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopping/search",
        json={"category": "Electronics", "max_price": 100, "limit": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["total"] == 1
    assert body["products"][0]["name"] == "QuietKeys Wireless Keyboard"


def test_smart_search_degrades_without_ai_services(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopping/smart-search",
        json={"query": "water bottle under $40"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback:fallback"
    assert body["products"][0]["name"] == "Summit Insulated Bottle"
    assert body["parsed_query"]["max_price"] == "40"


def test_smart_search_accepts_explicit_ui_filters(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopping/smart-search",
        json={"query": "", "category": "Electronics", "max_price": 100},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback:filters"
    assert [product["name"] for product in body["products"]] == [
        "QuietKeys Wireless Keyboard"
    ]
    assert body["parsed_query"]["category"] == "Electronics"
    assert body["parsed_query"]["max_price"] == "100"


def test_validation_rejects_invalid_price_range(client: TestClient) -> None:
    response = client.post(
        "/api/v1/shopping/search",
        json={"min_price": 100, "max_price": 10},
    )
    assert response.status_code == 422


def test_api_key_is_enforced_when_configured(client: TestClient) -> None:
    settings.api_key = "test-secret"
    assert client.get("/api/v1/system/health").status_code == 401
    assert (
        client.get(
            "/api/v1/system/health", headers={"X-API-Key": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/system/health", headers={"X-API-Key": "test-secret"}
        ).status_code
        == 200
    )
