from graph.state import GraphState
from config import STATUS_FAILED
from normalizer.normalizer import normalize_raw_prompt


def normalize_input_node(state: GraphState) -> GraphState:
    raw_input = state.get("raw_input", "").strip()

    result = normalize_raw_prompt(raw_input)

    if result["success"] is False:
        return {
            **state,
            "normalized_input": None,
            "normalization_success": False,
            "normalization_error": result["error"],
            "normalization_debug": result.get("debug", {}),
            "status": STATUS_FAILED,
            "failure_stage": "normalization",
        }

    return {
        **state,
        "normalized_input": result["normalized_input"],
        "normalization_success": True,
        "normalization_error": None,
        "normalization_debug": result.get("debug", {}),
    }