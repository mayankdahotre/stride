from typing import Literal, TypedDict

Intent = Literal["search", "compare", "recommend", "plan"]


class CommerceState(TypedDict, total=False):
    content: str
    explicit_intent: Intent | None
    intent: Intent
    extracted: dict[str, object]
    candidates: list[dict[str, object]]
    products: list[dict[str, object]]
    comparison: dict[str, object] | None
    recommendation: dict[str, object] | None
    plan: dict[str, object] | None
    content_out: str
    clarification: bool
    model_source: str
