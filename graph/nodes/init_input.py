from graph.state import GraphState
from config import STATUS_INITIALIZED


def init_input_node(state: GraphState) -> GraphState:
    return {
        **state,
        "status": STATUS_INITIALIZED,
        "failure_stage": None,
    }