from graph.state import GraphState
from config import STATUS_PARSED, STATUS_FAILED, FAILURE_PARSE


def parse_trace_node(state: GraphState) -> GraphState:
    raw_output = state.get("raw_llm_output", "").strip()

    if not raw_output:
        return {
            **state,
            "parse_success": False,
            "parse_error": "Empty LLM output.",
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_PARSE,
        }

    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]

    if not lines or not lines[0].startswith("Answer:"):
        return {
            **state,
            "parse_success": False,
            "parse_error": "Missing or malformed 'Answer:' line.",
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_PARSE,
        }

    answer = lines[0].replace("Answer:", "").strip()

    if len(lines) < 2 or lines[1] != "Steps:":
        return {
            **state,
            "parse_success": False,
            "parse_error": "Missing 'Steps:' line.",
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_PARSE,
        }

    steps = []
    for line in lines[2:]:
        if not line.startswith("S"):
            continue
        steps.append(line)

    if not steps:
        return {
            **state,
            "parse_success": False,
            "parse_error": "No reasoning steps found.",
            "status": STATUS_FAILED,
            "failure_stage": FAILURE_PARSE,
        }

    parsed_trace = {
        "answer": answer,
        "steps": steps,
    }

    return {
        **state,
        "parsed_trace": parsed_trace,
        "parse_success": True,
        "parse_error": None,
        "status": STATUS_PARSED,
    }