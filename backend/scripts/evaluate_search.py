"""Compare keyword and hybrid search on a small, repeatable relevance set."""

import asyncio
import json
import os
from pathlib import Path

import httpx

from app.core.config import settings

CASES_PATH = Path(__file__).parents[1] / "evaluations" / "search_cases.json"


async def evaluate() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    headers = {"X-API-Key": settings.api_key} if settings.api_key else {}
    scores = {"keyword": 0, "hybrid": 0}

    async with httpx.AsyncClient(
        base_url=os.getenv("EVALUATION_API_URL", "http://127.0.0.1:8000"),
        headers=headers,
        timeout=180,
    ) as client:
        for case in cases:
            payload = {"query": case["query"], "limit": 3}
            keyword = (
                await client.post("/api/v1/shopping/search", json=payload)
            ).raise_for_status().json()
            hybrid = (
                await client.post("/api/v1/shopping/smart-search", json=payload)
            ).raise_for_status().json()
            expected = case["expected_product"]
            keyword_names = [item["name"] for item in keyword["products"]]
            hybrid_names = [item["name"] for item in hybrid["products"]]
            scores["keyword"] += expected in keyword_names
            scores["hybrid"] += expected in hybrid_names
            print(
                json.dumps(
                    {
                        "query": case["query"],
                        "expected": expected,
                        "keyword_top_3": keyword_names,
                        "hybrid_top_3": hybrid_names,
                    }
                )
            )

    print(json.dumps({"cases": len(cases), "hits_at_3": scores}))
    if scores["hybrid"] < scores["keyword"]:
        raise SystemExit("Hybrid relevance regressed below keyword search")


if __name__ == "__main__":
    asyncio.run(evaluate())
