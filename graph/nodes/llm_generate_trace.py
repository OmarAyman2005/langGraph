from typing import Any, Dict

from llm_response.llm_response_generator import generate_llm_response


def llm_generate_trace_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node wrapper for the LLM Response Generator.

    Expected state input:
    - normalized_input

    Added state output:
    - raw_llm_output
    - llm_response_generation
    """

    normalized_input = state.get("normalized_input")

    generation_result = generate_llm_response(normalized_input)

    if generation_result["generation_success"] is False:
        return {
            **state,
            "pipeline_status": "failed",
            "error_component": "llm_response_generator",
            "error_message": generation_result["generation_error"],
            "raw_llm_output": None,
            "llm_response_generation": generation_result,
        }

    return {
        **state,
        "raw_llm_output": generation_result["raw_llm_output"],
        "llm_response_generation": generation_result,
    }