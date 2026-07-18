"""Evaluate compare/recommend/plan conversation intents offline against the API."""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx

from app.core.config import settings

CASES_PATH = Path(__file__).parents[1] / "evaluations" / "conversation_cases.json"


def _parse_done(payload: str) -> dict[str, object]:
    done: dict[str, object] | None = None
    event = "message"
    data_lines: list[str] = []
    for line in payload.splitlines():
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif line == "" and data_lines:
            if event == "done":
                done = json.loads("\n".join(data_lines))
            event = "message"
            data_lines = []
    if data_lines and event == "done":
        done = json.loads("\n".join(data_lines))
    if done is None:
        raise RuntimeError("Stream ended without a done event")
    return done


async def evaluate() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    headers = {"X-API-Key": settings.api_key} if settings.api_key else {}
    passed = 0

    async with httpx.AsyncClient(
        base_url=os.getenv("EVALUATION_API_URL", "http://127.0.0.1:8000"),
        headers=headers,
        timeout=180,
    ) as client:
        for case in cases:
            created = (
                await client.post("/api/v1/conversations")
            ).raise_for_status().json()
            response = await client.post(
                f"/api/v1/conversations/{created['thread_id']}/messages/stream",
                headers={"X-Conversation-Token": created["conversation_token"]},
                json={
                    "content": case["query"],
                    "request_id": str(uuid4()),
                    "intent": case.get("intent"),
                },
            )
            response.raise_for_status()
            done = _parse_done(response.text)
            expect = case["expect"]
            ok = done.get("intent") == expect["intent"]
            if expect.get("clarification"):
                ok = ok and bool(done.get("clarification"))
            if expect.get("requires_comparison"):
                ok = ok and done.get("comparison") is not None
            if expect.get("requires_recommendation"):
                ok = ok and done.get("recommendation") is not None
            if expect.get("requires_plan"):
                ok = ok and done.get("plan") is not None
            if "expected_product" in expect:
                product = (done.get("recommendation") or {}).get("product", {})
                ok = ok and product.get("name") == expect["expected_product"]
            if "max_total" in expect:
                ok = ok and float((done.get("plan") or {}).get("total", "inf")) <= expect[
                    "max_total"
                ]
            if "min_products" in expect:
                ok = ok and len(done.get("products") or []) >= expect["min_products"]
            passed += int(ok)
            print(
                json.dumps(
                    {
                        "query": case["query"],
                        "ok": ok,
                        "intent": done.get("intent"),
                        "clarification": done.get("clarification"),
                        "products": [
                            item.get("name") for item in done.get("products") or []
                        ],
                    }
                )
            )

    summary = {"cases": len(cases), "passed": passed}
    print(json.dumps(summary))
    if passed < len(cases):
        raise SystemExit("Conversation evaluation failed")


if __name__ == "__main__":
    asyncio.run(evaluate())
