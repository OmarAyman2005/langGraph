from graph.state import GraphState
from config import STATUS_COMPLETED


def build_result_node(state: GraphState) -> GraphState:
    final_result = {
        "normalized_input": state.get("normalized_input"),
        "normalization_success": state.get("normalization_success"),
        "normalization_error": state.get("normalization_error"),

        "parsed_problem": state.get("parsed_problem"),
        "prompt_parse_success": state.get("prompt_parse_success"),
        "prompt_parse_error": state.get("prompt_parse_error"),

        "premises": state.get("premises", []),
        "question": state.get("question", ""),

        "raw_llm_output": state.get("raw_llm_output"),

        "parsed_trace": state.get("parsed_trace"),
        "response_parse_success": state.get("response_parse_success"),
        "response_parse_error": state.get("response_parse_error"),

        "symbolic_problem": state.get("symbolic_problem"),
        "symbolic_trace": state.get("symbolic_trace"),
        "translation_success": state.get("translation_success"),
        "translation_error": state.get("translation_error"),

        "verification_result": state.get("verification_result"),
        "verification_success": state.get("verification_success"),
        "verification_error": state.get("verification_error"),

        "status": state.get("status"),
        "failure_stage": state.get("failure_stage"),
    }

    return {
        **state,
        "final_result": final_result,
        "status": STATUS_COMPLETED if state.get("failure_stage") is None else state.get("status"),
    }