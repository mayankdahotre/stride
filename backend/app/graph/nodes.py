import json
import re
from decimal import Decimal

from app.graph.gateway import (
    CommerceExtraction,
    Explanation,
    IntentDecision,
    gateway,
)
from app.graph.state import CommerceState, Intent

INTENT_WORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    ("compare", ("compare", "versus", " vs ", "difference")),
    ("plan", ("plan", "complete kit", "setup", "bundle")),
    ("recommend", ("recommend", "best for me", "which should", "suggest")),
)


def heuristic_intent(content: str) -> Intent:
    lowered = f" {content.casefold()} "
    for intent, markers in INTENT_WORDS:
        if any(marker in lowered for marker in markers):
            return intent
    return "search"


def heuristic_extraction(content: str) -> CommerceExtraction:
    lowered = content.casefold()
    budget_match = re.search(
        r"(?:under|within|budget(?:\s+of)?)\s*\$?(\d+(?:\.\d{1,2})?)", lowered
    )
    explicit_ids = re.findall(r"(?:product|id|#)\s*#?(\d+)", lowered)
    words = re.findall(r"[a-z][a-z0-9'-]*", lowered)
    ignored = {
        "compare", "recommend", "search", "find", "show", "plan", "product",
        "products", "under", "within", "budget", "with", "for", "and", "the",
        "versus", "best", "me", "of", "a", "an", "to", "kit",
    }
    return CommerceExtraction(
        keywords=[word for word in dict.fromkeys(words) if word not in ignored][:20],
        product_ids=[int(value) for value in explicit_ids],
        budget=float(budget_match.group(1)) if budget_match else None,
    )


async def classify_and_extract(state: CommerceState) -> dict[str, object]:
    fallback_intent = heuristic_intent(state["content"])
    fallback_extraction = heuristic_extraction(state["content"])
    if state.get("explicit_intent"):
        intent = state["explicit_intent"]
        source = "explicit"
    else:
        try:
            decision = await gateway.structured(
                IntentDecision,
                "Classify into exactly one intent: search, compare, recommend, plan.",
                state["content"],
            )
            intent = decision.intent
            source = "ollama"
        except Exception:
            intent = fallback_intent
            source = "fallback"
    try:
        model_extraction = await gateway.structured(
            CommerceExtraction,
            "Extract only stated shopping constraints. Never invent product IDs.",
            state["content"],
        )
        extracted = model_extraction.model_dump()
        # Numeric constraints explicitly present in user text are authoritative.
        if fallback_extraction.budget is not None:
            extracted["budget"] = fallback_extraction.budget
        extracted["keywords"] = list(
            dict.fromkeys(
                [*fallback_extraction.keywords, *model_extraction.keywords]
            )
        )[:20]
    except Exception:
        extracted = fallback_extraction.model_dump()
    candidate_ids = {int(item["id"]) for item in state.get("candidates", [])}
    extracted["product_ids"] = [
        value for value in extracted.get("product_ids", []) if value in candidate_ids
    ]
    return {"intent": intent, "extracted": extracted, "model_source": source}


def _named_candidates(state: CommerceState) -> list[dict[str, object]]:
    content = state["content"].casefold()
    candidates = state.get("candidates", [])
    named = [item for item in candidates if str(item["name"]).casefold() in content]
    requested = set(state.get("extracted", {}).get("product_ids", []))
    by_id = [item for item in candidates if item["id"] in requested]
    return list({item["id"]: item for item in [*named, *by_id]}.values())


async def search_node(state: CommerceState) -> dict[str, object]:
    products = state.get("candidates", [])[:8]
    return {"products": products, "content_out": f"Found {len(products)} products."}


async def compare_node(state: CommerceState) -> dict[str, object]:
    selected = _named_candidates(state)
    if len(selected) < 2:
        return {
            "products": selected,
            "comparison": None,
            "clarification": True,
            "content_out": "Please name at least two products to compare.",
        }
    selected = selected[:4]
    keys = sorted(
        set().union(
            *(set(item.get("specifications", {})) for item in selected)
        )
    )
    rows = [
        {
            "name": key,
            "values": {
                str(item["id"]): item.get("specifications", {}).get(key)
                for item in selected
            },
        }
        for key in keys
    ]
    prices = [Decimal(str(item["price"])) for item in selected]
    comparison = {
        "products": selected,
        "specifications": rows,
        "price_difference": str(max(prices) - min(prices)),
        "currency": selected[0]["currency"],
    }
    return {
        "products": selected,
        "comparison": comparison,
        "clarification": False,
        "content_out": f"Compared {len(selected)} products.",
    }


async def recommend_node(state: CommerceState) -> dict[str, object]:
    products = state.get("candidates", [])
    if not products:
        return {
            "products": [],
            "recommendation": None,
            "content_out": "I could not find a matching product.",
        }
    product = products[0]
    recommendation = {
        "product": product,
        "reason": "Top deterministic match by relevance, rating, price, and availability.",
    }
    return {
        "products": [product],
        "recommendation": recommendation,
        "content_out": f"I recommend {product['name']}.",
    }


async def plan_node(state: CommerceState) -> dict[str, object]:
    candidates = state.get("candidates", [])
    budget_value = state.get("extracted", {}).get("budget")
    budget = Decimal(str(budget_value)) if budget_value is not None else None
    chosen: list[dict[str, object]] = []
    total = Decimal("0")
    for product in candidates:
        price = Decimal(str(product["price"]))
        if budget is None or total + price <= budget:
            chosen.append(product)
            total += price
    plan = {
        "items": chosen,
        "total": str(total),
        "currency": chosen[0]["currency"] if chosen else "USD",
        "budget": str(budget) if budget is not None else None,
        "remaining": str(budget - total) if budget is not None else None,
    }
    return {
        "products": chosen,
        "plan": plan,
        "content_out": f"Built a {len(chosen)}-item plan totaling ${total}.",
    }


async def explain_node(state: CommerceState) -> dict[str, object]:
    deterministic = state["content_out"]
    facts = {
        "intent": state["intent"],
        "product_names": [item["name"] for item in state.get("products", [])],
        "comparison": state.get("comparison"),
        "recommendation": state.get("recommendation"),
        "plan": state.get("plan"),
    }
    try:
        result = await gateway.structured(
            Explanation,
            (
                "Explain the supplied deterministic commerce result concisely. "
                "Do not add products, prices, IDs, or facts."
            ),
            json.dumps(facts, default=str),
        )
        return {"content_out": result.explanation}
    except Exception:
        return {"content_out": deterministic}
