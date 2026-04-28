from graph.state import GraphState
from config import STATUS_FAILED, STATUS_PARSED
from parser.trace_parser import parse_llm_response


def parse_llm_response_node(state: GraphState) -> GraphState:
    raw_output = state.get("raw_llm_output", "")

    result = parse_llm_response(raw_output)

    if result["response_parse_success"] is False:
        return {
            **state,
            "response_parse_success": False,
            "response_parse_error": result["response_parse_error"],
            "status": STATUS_FAILED,
            "failure_stage": "response_parse",
        }

    return {
        **state,
        "parsed_trace": result["trace"],
        "response_parse_success": True,
        "response_parse_error": None,
        "status": STATUS_PARSED,
    }