from graph.state import GraphState
from config import STATUS_TRANSLATED, STATUS_FAILED, FAILURE_TRANSLATION
from translator.translator import translate_problem_and_trace


def translate_trace_node(state: GraphState) -> GraphState:
    parsed_problem = state.get("parsed_problem")
    parsed_trace = state.get("parsed_trace")

    result = translate_problem_and_trace(parsed_problem, parsed_trace)

    if result["translation_success"] is False:
        return {
            **state,
            "translation_success": False,
            "translation_error": result["translation_error"],
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_TRANSLATION,
        }

    return {
        **state,
        "symbolic_problem": result["symbolic_problem"],
        "symbolic_trace": result["symbolic_trace"],
        "translation_success": True,
        "translation_error": None,
        "status": STATUS_TRANSLATED,
    }