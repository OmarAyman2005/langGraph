from graph.state import GraphState
from config import STATUS_FAILED
from parsers.normalized_prompt_parser import parse_normalized_prompt


def parse_normalized_prompt_node(state: GraphState) -> GraphState:
    normalized_input = state.get("normalized_input", "")

    result = parse_normalized_prompt(normalized_input)

    if result["prompt_parse_success"] is False:
        return {
            **state,
            "prompt_parse_success": False,
            "prompt_parse_error": result["prompt_parse_error"],
            "status": STATUS_FAILED,
            "failure_stage": "prompt_parse",
        }

    problem = result["problem"]

    return {
        **state,
        "prompt_parse_success": True,
        "prompt_parse_error": None,
        "parsed_problem": problem,
        "premises": list(problem["premises"].values()),
        "question": problem["question"],
    }