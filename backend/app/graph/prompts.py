"""System prompts shared by the LangGraph nodes and the QLoRA dataset."""

INTENT_SYSTEM = "Classify into exactly one intent: search, compare, recommend, plan."
EXTRACT_SYSTEM = "Extract only stated shopping constraints. Never invent product IDs."
EXPLAIN_SYSTEM = (
    "Explain the supplied deterministic commerce result concisely. "
    "Do not add products, prices, IDs, or facts."
)
