import json
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langgraph.graph.state import CompiledStateGraph

from app.graph.builder import build_graph, route_intent
from app.graph.gateway import CommerceExtraction, Explanation, IntentDecision, gateway
from app.graph.nodes import classify_and_extract, compare_node, heuristic_intent
from app.graph.state import CommerceState
from app.repositories.conversations import ConversationRepository, clear_memory_conversations
from app.repositories.products import ProductRepository
from app.schemas.shopping import ProductResponse


def _parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for block in re.split(r"\n\n+", body.strip()):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").strip())
        events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def _create_thread(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/conversations")
    assert response.status_code == 201
    body = response.json()
    return body["thread_id"], body["conversation_token"]


def _stream(
    client: TestClient,
    thread_id: str,
    token: str,
    content: str,
    *,
    intent: str | None = None,
    request_id: str | None = None,
) -> list[tuple[str, dict[str, object]]]:
    payload: dict[str, object] = {
        "content": content,
        "request_id": request_id or str(uuid4()),
    }
    if intent is not None:
        payload["intent"] = intent
    response = client.post(
        f"/api/v1/conversations/{thread_id}/messages/stream",
        headers={"X-Conversation-Token": token},
        json=payload,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return _parse_sse(response.text)


def test_create_conversation_payload(client: TestClient) -> None:
    response = client.post("/api/v1/conversations")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"thread_id", "conversation_token", "title", "created_at"}
    assert body["title"] == "New conversation"
    assert len(body["conversation_token"]) >= 32


def test_token_isolation(client: TestClient) -> None:
    thread_id, token = _create_thread(client)
    other = client.post("/api/v1/conversations").json()
    denied = client.get(
        f"/api/v1/conversations/{thread_id}",
        headers={"X-Conversation-Token": other["conversation_token"]},
    )
    assert denied.status_code == 404
    allowed = client.get(
        f"/api/v1/conversations/{thread_id}",
        headers={"X-Conversation-Token": token},
    )
    assert allowed.status_code == 200
    assert allowed.json()["thread_id"] == thread_id
    assert allowed.json()["messages"] == []


@pytest.mark.parametrize(
    ("content", "intent"),
    [
        ("Find running shoes under 100", "search"),
        ("Compare TrailBlaze Running Shoes and Velocity Carbon Racer", "compare"),
        ("Recommend the best yoga mat", "recommend"),
        ("Plan a fitness kit under 150", "plan"),
    ],
)
def test_four_intent_routes(client: TestClient, content: str, intent: str) -> None:
    thread_id, token = _create_thread(client)
    events = _stream(client, thread_id, token, content, intent=intent)
    names = [name for name, _ in events]
    assert names[0] == "metadata"
    assert "status" in names
    assert names[-1] == "done"
    done = events[-1][1]
    assert done["intent"] == intent
    assert done["message"]["role"] == "assistant"
    assert done["message"]["content"]
    assert done["message"]["intent"] == intent
    if intent == "search":
        assert "products" in names
        assert done["products"]
    if intent == "compare":
        assert "comparison" in names
        assert done["comparison"] is not None
    if intent == "recommend":
        assert "recommendation" in names
        assert done["recommendation"]["product"]["name"]
    if intent == "plan":
        assert "plan" in names
        assert float(done["plan"]["total"]) <= 150


def test_compare_clarifies_without_two_products(client: TestClient) -> None:
    thread_id, token = _create_thread(client)
    events = _stream(
        client,
        thread_id,
        token,
        "compare these two mystery items",
        intent="compare",
    )
    done = events[-1][1]
    assert done["clarification"] is True
    assert "two products" in done["message"]["content"].casefold()


def test_sse_event_order_and_framing(client: TestClient) -> None:
    thread_id, token = _create_thread(client)
    events = _stream(
        client,
        thread_id,
        token,
        "Recommend QuietKeys Wireless Keyboard",
        intent="recommend",
    )
    names = [name for name, _ in events]
    assert names[:2] == ["metadata", "status"]
    assert "recommendation" in names
    assert "token" in names
    assert names[-1] == "done"
    assert events[0][1]["thread_id"] == thread_id
    assert "request_id" in events[0][1]


def test_request_id_idempotency(client: TestClient) -> None:
    thread_id, token = _create_thread(client)
    request_id = str(uuid4())
    first = _stream(
        client,
        thread_id,
        token,
        "Find running shoes",
        intent="search",
        request_id=request_id,
    )
    second = _stream(
        client,
        thread_id,
        token,
        "Find running shoes",
        intent="search",
        request_id=request_id,
    )
    assert second[1][1]["stage"] == "idempotent_replay"
    assert first[-1][1]["message"] == second[-1][1]["message"]
    history = client.get(
        f"/api/v1/conversations/{thread_id}",
        headers={"X-Conversation-Token": token},
    ).json()
    assistants = [item for item in history["messages"] if item["role"] == "assistant"]
    assert len(assistants) == 1


def test_persistence_memory_fallback() -> None:
    clear_memory_conversations()
    repository = ConversationRepository(None)
    thread, token = repository.create("Offline thread")
    assert repository.get_authorized(thread.id, "wrong") is None
    assert repository.get_authorized(thread.id, token) is not None
    request_id = uuid4()
    envelope = {
        "message": {"role": "assistant", "content": "hello", "intent": "search"},
        "intent": "search",
        "products": [],
        "comparison": None,
        "recommendation": None,
        "plan": None,
        "clarification": False,
        "model_source": "fallback",
        "catalog_source": "fallback",
    }
    saved = repository.save_exchange(
        thread.id, request_id, "hi", "search", envelope
    )
    assert repository.get_cached(thread.id, request_id) == saved
    assert repository.serialize(thread)["title"] == "Offline thread"


def test_graph_is_real_state_graph() -> None:
    graph = build_graph()
    assert isinstance(graph, CompiledStateGraph)
    assert route_intent({"intent": "recommend"}) == "recommend"


@pytest.mark.asyncio
async def test_graph_routing_and_intents() -> None:
    graph = build_graph()
    candidates = [
        ProductResponse.model_validate(product).model_dump(mode="json")
        for product in ProductRepository(None).search_candidates("running shoes")[0]
    ]
    for intent, content in (
        ("search", "running shoes"),
        ("compare", "Compare TrailBlaze Running Shoes and Velocity Carbon Racer"),
        ("recommend", "recommend a running shoe"),
        ("plan", "plan a running kit under 300"),
    ):
        result = await graph.ainvoke(
            {
                "content": content,
                "explicit_intent": intent,
                "candidates": candidates,
            },
            config={"configurable": {"thread_id": str(uuid4())}},
        )
        assert result["intent"] == intent
        assert result["content_out"]


@pytest.mark.asyncio
async def test_model_failure_and_malformed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*_args: object, **_kwargs: object) -> object:
        raise ValueError("malformed")

    monkeypatch.setattr(gateway, "structured", boom)
    state: CommerceState = {
        "content": "compare TrailBlaze Running Shoes and Velocity Carbon Racer",
        "candidates": [
            ProductResponse.model_validate(product).model_dump(mode="json")
            for product in ProductRepository(None).search_candidates(
                "TrailBlaze Velocity"
            )[0]
        ],
    }
    classified = await classify_and_extract(state)
    assert classified["intent"] == "compare"
    assert classified["model_source"] == "fallback"
    assert heuristic_intent("please recommend something") == "recommend"


@pytest.mark.asyncio
async def test_hallucinated_product_ids_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def hallucinate(schema: type[object], *_args: object, **_kwargs: object):
        if schema is IntentDecision:
            return IntentDecision(intent="compare")
        if schema is CommerceExtraction:
            return CommerceExtraction(product_ids=[9999, 1])
        return Explanation(explanation="ignored")

    monkeypatch.setattr(gateway, "structured", hallucinate)
    candidates = [
        ProductResponse.model_validate(product).model_dump(mode="json")
        for product in ProductRepository(None).get_by_ids([1, 9])[0]
    ]
    result = await classify_and_extract(
        {
            "content": "compare product 9999 and product 1",
            "candidates": candidates,
        }
    )
    assert result["extracted"]["product_ids"] == [1]


@pytest.mark.asyncio
async def test_compare_node_clarification_without_candidates() -> None:
    result = await compare_node(
        {"content": "compare these", "candidates": [], "extracted": {}}
    )
    assert result["clarification"] is True
    assert result["comparison"] is None


def test_repository_get_by_ids_respects_candidates() -> None:
    products, source = ProductRepository(None).get_by_ids(
        [1, 9, 999], candidate_ids={1, 9}
    )
    assert source == "fallback"
    assert [product.id for product in products] == [1, 9]


def test_seed_products_expose_comparison_specs() -> None:
    products = ProductRepository(None).search_candidates("running")[0]
    assert products
    assert products[0].sku
    assert products[0].sport
    assert products[0].brand
    assert isinstance(products[0].specifications, dict)
    assert products[0].in_stock is True
