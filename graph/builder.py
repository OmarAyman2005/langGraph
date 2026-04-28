from langgraph.graph import StateGraph, END

from graph.state import GraphState
from graph.nodes import (
    init_input_node,
    normalize_input_node,
    build_result_node,
)


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("init_input", init_input_node)
    graph.add_node("normalize_input", normalize_input_node)
    graph.add_node("build_result", build_result_node)

    graph.set_entry_point("init_input")

    graph.add_edge("init_input", "normalize_input")
    graph.add_edge("normalize_input", "build_result")
    graph.add_edge("build_result", END)

    return graph.compile()