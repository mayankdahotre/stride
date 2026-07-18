import json
import logging
import re

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.shopping import ParsedQuery

logger = logging.getLogger(__name__)

KNOWN_CATEGORIES = {
    "bag": "Bags",
    "bags": "Bags",
    "backpack": "Bags",
    "clothes": "Clothing",
    "clothing": "Clothing",
    "electronics": "Electronics",
    "fitness": "Fitness",
    "footwear": "Footwear",
    "outdoor": "Outdoors",
    "outdoors": "Outdoors",
    "shoe": "Footwear",
    "shoes": "Footwear",
}
STOP_WORDS = {
    "a", "an", "and", "at", "below", "between", "find", "for", "from", "i", "in",
    "looking", "me", "of", "or", "over", "show", "than", "the", "to", "under",
    "want", "with",
}


class QueryParser:
    async def parse(self, query: str) -> tuple[ParsedQuery, str]:
        try:
            ai_result = await self._parse_with_ollama(query)
            deterministic = self.parse_deterministically(query)
            has_deterministic_price = (
                deterministic.min_price is not None
                or deterministic.max_price is not None
            )
            return (
                ParsedQuery(
                    keywords=list(
                        dict.fromkeys(
                            [*deterministic.keywords, *ai_result.keywords]
                        )
                    )[:20],
                    # Categories become hard database filters, so only accept
                    # one explicitly named in the query. Model-inferred
                    # categories can otherwise hide semantically useful items.
                    category=deterministic.category,
                    min_price=(
                        deterministic.min_price
                        if has_deterministic_price
                        else ai_result.min_price
                    ),
                    max_price=(
                        deterministic.max_price
                        if has_deterministic_price
                        else ai_result.max_price
                    ),
                ),
                "ollama",
            )
        except (
            httpx.HTTPError,
            ValidationError,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            logger.info("Ollama parser unavailable; using deterministic parser: %s", exc)
            return self.parse_deterministically(query), "fallback"

    async def _parse_with_ollama(self, query: str) -> ParsedQuery:
        prompt = (
            "Extract shopping search filters. Use only facts stated by the user. "
            "Category must be one of Bags, Clothing, Electronics, Fitness, "
            "Footwear, or Outdoors; otherwise use null. "
            "Return JSON matching the supplied schema.\nUser query: " + query
        )
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "format": ParsedQuery.model_json_schema(),
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=settings.model_request_timeout) as client:
            response = await client.post(
                f"{settings.ollama_url.rstrip('/')}/api/chat", json=payload
            )
            response.raise_for_status()
        content = response.json()["message"]["content"]
        return ParsedQuery.model_validate_json(content)

    @staticmethod
    def parse_deterministically(query: str) -> ParsedQuery:
        lowered = query.casefold()
        category = next(
            (label for term, label in KNOWN_CATEGORIES.items() if re.search(rf"\b{re.escape(term)}\b", lowered)),
            None,
        )
        min_price = None
        max_price = None
        between = re.search(
            r"\bbetween\s+\$?(\d+(?:\.\d{1,2})?)\s+(?:and|to)\s+\$?(\d+(?:\.\d{1,2})?)",
            lowered,
        )
        if between:
            min_price, max_price = between.group(1), between.group(2)
        else:
            upper = re.search(
                r"\b(?:under|below|less than|up to)\s+\$?(\d+(?:\.\d{1,2})?)",
                lowered,
            )
            lower = re.search(
                r"\b(?:over|above|more than|at least)\s+\$?(\d+(?:\.\d{1,2})?)",
                lowered,
            )
            max_price = upper.group(1) if upper else None
            min_price = lower.group(1) if lower else None

        words = re.findall(r"[a-z0-9][a-z0-9'-]*", lowered)
        category_terms = set(KNOWN_CATEGORIES)
        keywords = [
            word
            for word in dict.fromkeys(words)
            if word not in STOP_WORDS
            and word not in category_terms
            and not word.replace(".", "", 1).isdigit()
        ]
        return ParsedQuery(
            keywords=keywords[:20],
            category=category,
            min_price=min_price,
            max_price=max_price,
        )
