from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    classify_and_extract,
    compare_node,
    explain_node,
    plan_node,
    recommend_node,
    search_node,
)
from app.graph.state import CommerceState


def route_intent(state: CommerceState) -> str:
    return state["intent"]


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> object:
    builder = StateGraph(CommerceState)
    builder.add_node("classify", classify_and_extract)
    builder.add_node("search", search_node)
    builder.add_node("compare", compare_node)
    builder.add_node("recommend", recommend_node)
    builder.add_node("build_plan", plan_node)
    builder.add_node("explain", explain_node)
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_intent,
        {
            "search": "search",
            "compare": "compare",
            "recommend": "recommend",
            "plan": "build_plan",
        },
    )
    for node in ("search", "compare", "recommend", "build_plan"):
        builder.add_edge(node, "explain")
    builder.add_edge("explain", END)
    return builder.compile(checkpointer=checkpointer or MemorySaver())
