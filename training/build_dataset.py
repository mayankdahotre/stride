"""ChatML examples for the three JSON calls the Stride agent makes."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.graph.prompts import EXPLAIN_SYSTEM, EXTRACT_SYSTEM, INTENT_SYSTEM

DATA = Path(__file__).resolve().parent / "data"

SPORTS = ("Running", "Football", "Hiking", "Golf", "Tennis", "Yoga", "Cycling", "Swimming")
PRODUCTS = {
    "Running": "shoes",
    "Football": "boots",
    "Hiking": "backpack",
    "Golf": "clubs",
    "Tennis": "racket",
    "Yoga": "mat",
    "Cycling": "helmet",
    "Swimming": "goggles",
}


def examples() -> dict[str, list[dict]]:
    rows = [*_intent_rows(), *_extract_rows(), *_explain_rows()]
    valid = rows[::8]
    held = {id(row) for row in valid}
    return {"train": [row for row in rows if id(row) not in held], "valid": valid}


def write_dataset() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name, rows in examples().items():
        path = DATA / f"{name}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        print(f"{path.name}: {len(rows)}")


def _chat(system: str, user: str, payload: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(payload, separators=(",", ":"))},
        ]
    }


def _intent_rows() -> list[dict]:
    rows = []
    for sport, noun in PRODUCTS.items():
        rows.append(_chat(INTENT_SYSTEM, f"show me {sport.casefold()} {noun}", {"intent": "search"}))
        rows.append(_chat(INTENT_SYSTEM, f"{noun} under 5000", {"intent": "search"}))
        rows.append(
            _chat(INTENT_SYSTEM, f"compare {sport.casefold()} {noun} and the pro version", {"intent": "compare"})
        )
        rows.append(_chat(INTENT_SYSTEM, f"recommend a {sport.casefold()} {noun}", {"intent": "recommend"}))
        rows.append(
            _chat(INTENT_SYSTEM, f"plan a {sport.casefold()} kit under 15000", {"intent": "plan"})
        )
    rows.append(_chat(INTENT_SYSTEM, "what is the difference between MH500 and NH500", {"intent": "compare"}))
    rows.append(_chat(INTENT_SYSTEM, "which should I buy for trail running", {"intent": "recommend"}))
    rows.append(_chat(INTENT_SYSTEM, "build a complete camping setup", {"intent": "plan"}))
    return rows


def _extract_rows() -> list[dict]:
    rows = []
    for sport, noun in PRODUCTS.items():
        rows.append(
            _chat(
                EXTRACT_SYSTEM,
                f"show me {sport.casefold()} {noun}",
                {"keywords": [sport.casefold(), noun], "product_ids": [], "sport": sport, "budget": None},
            )
        )
        rows.append(
            _chat(
                EXTRACT_SYSTEM,
                f"{sport.casefold()} {noun} under 8000",
                {"keywords": [sport.casefold(), noun], "product_ids": [], "sport": sport, "budget": 8000},
            )
        )
    rows.append(
        _chat(
            EXTRACT_SYSTEM,
            "compare product 12 and product 18",
            {"keywords": ["compare"], "product_ids": [12, 18], "sport": None, "budget": None},
        )
    )
    rows.append(
        _chat(
            EXTRACT_SYSTEM,
            "recommend something",
            {"keywords": ["recommend", "something"], "product_ids": [], "sport": None, "budget": None},
        )
    )
    return rows


def _explain_rows() -> list[dict]:
    cases = [
        (
            {
                "intent": "recommend",
                "product_names": ["Kiprun KS900"],
                "comparison": None,
                "recommendation": {"reason": "Top deterministic match by relevance, rating, price, and availability."},
                "plan": None,
            },
            "I recommend the Kiprun KS900. It is the top match by relevance, rating, price, and availability.",
        ),
        (
            {
                "intent": "search",
                "product_names": ["Quechua MH500", "Quechua NH500"],
                "comparison": None,
                "recommendation": None,
                "plan": None,
            },
            "Found the Quechua MH500 and the Quechua NH500.",
        ),
        (
            {
                "intent": "compare",
                "product_names": ["Quechua MH500", "Quechua NH500"],
                "comparison": {"price_difference": "1500"},
                "recommendation": None,
                "plan": None,
            },
            "Compared the Quechua MH500 and the Quechua NH500.",
        ),
        (
            {
                "intent": "plan",
                "product_names": ["Inesis irons", "Inesis golf balls"],
                "comparison": None,
                "recommendation": None,
                "plan": {"total": "9998"},
            },
            "The plan includes Inesis irons and Inesis golf balls.",
        ),
    ]
    rows = []
    for facts, explanation in cases:
        for sport in SPORTS[:4]:
            named = dict(facts)
            if named["intent"] == "search":
                named = {
                    **facts,
                    "product_names": [f"{sport} shoes"],
                }
                text = f"Found {sport} shoes."
            else:
                text = explanation
            rows.append(_chat(EXPLAIN_SYSTEM, json.dumps(named), {"explanation": text}))
    return rows


if __name__ == "__main__":
    write_dataset()
