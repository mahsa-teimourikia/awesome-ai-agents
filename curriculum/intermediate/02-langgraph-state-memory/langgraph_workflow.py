"""Optional LangGraph version of a bounded review workflow.

Run after installing requirements.txt. The graph makes state transitions
explicit; real model and tool calls should still be policy-checked at the edge.
"""
from typing import TypedDict
from langgraph.graph import END, START, StateGraph


class ReviewState(TypedDict):
    draft: str
    approved: bool
    attempts: int


def write_draft(state: ReviewState) -> ReviewState:
    return {**state, "draft": "draft grounded in the supplied evidence", "attempts": state["attempts"] + 1}


def review(state: ReviewState) -> ReviewState:
    return {**state, "approved": bool(state["draft"])}


def route(state: ReviewState) -> str:
    return "done" if state["approved"] or state["attempts"] >= 2 else "rewrite"


graph = StateGraph(ReviewState)
graph.add_node("write", write_draft)
graph.add_node("review", review)
graph.add_edge(START, "write")
graph.add_edge("write", "review")
graph.add_conditional_edges("review", route, {"rewrite": "write", "done": END})
workflow = graph.compile()


if __name__ == "__main__":
    print(workflow.invoke({"draft": "", "approved": False, "attempts": 0}))
