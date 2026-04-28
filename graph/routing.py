from graph.state import GraphState


def route_after_prompt_parse(state: GraphState) -> str:
    if state.get("prompt_parse_success") is True:
        return "build_result"
    return "build_result"


def route_after_response_parse(state: GraphState) -> str:
    if state.get("response_parse_success") is True:
        return "translate_trace"
    return "build_result"


def route_after_translate(state: GraphState) -> str:
    if state.get("translation_success") is True:
        return "verify_trace"
    return "build_result"


def route_after_verify(state: GraphState) -> str:
    return "build_result"