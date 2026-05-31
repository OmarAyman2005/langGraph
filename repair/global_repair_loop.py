from typing import Any, Callable, Dict, List, Optional

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from llm_response.llm_response_generator import generate_llm_response
from parsers.llm_response_parser import parse_llm_response
from translator.translator import translate_problem_and_trace
from verifier.verifier import verify_symbolic_trace
from repair.repair_policy import build_repair_message


MAX_REPAIR_ATTEMPTS = 3


def make_pipeline_failure(
    error_component: str,
    error_message: str,
    partial_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = partial_state or {}

    return {
        **state,
        "pipeline_success": False,
        "pipeline_status": "failed",
        "error_component": error_component,
        "error_message": error_message,
        "final_result": None,
    }


def make_pipeline_success(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **state,
        "pipeline_success": True,
        "pipeline_status": "success",
        "error_component": None,
        "error_message": None,
        "final_result": state.get("verification_result"),
    }


def run_full_pipeline_once(raw_input: str) -> Dict[str, Any]:
    """
    Runs the full current pipeline once, without repair.

    Pipeline:
    Raw Input
    → Normalizer
    → Parser 1
    → LLM Response Generator
    → Parser 2
    → Translator
    → Verifier
    """

    state: Dict[str, Any] = {
        "raw_input": raw_input,
    }

    # ==================================================
    # Full Normalizer
    # ==================================================
    normalizer_result = normalize_raw_prompt(raw_input)
    state["normalizer_result"] = normalizer_result

    if normalizer_result["success"] is False:
        return make_pipeline_failure(
            error_component="normalizer",
            error_message=normalizer_result.get("error"),
            partial_state=state,
        )

    normalized_input = normalizer_result["normalized_input"]
    state["normalized_input"] = normalized_input

    # ==================================================
    # Parser 1
    # ==================================================
    parser_1_result = parse_normalized_prompt(normalized_input)
    state["parser_1_result"] = parser_1_result

    if parser_1_result["prompt_parse_success"] is False:
        return make_pipeline_failure(
            error_component="parser_1",
            error_message=parser_1_result.get("prompt_parse_error"),
            partial_state=state,
        )

    parsed_problem = parser_1_result["problem"]
    state["parsed_problem"] = parsed_problem

    # ==================================================
    # LLM Response Generator
    # ==================================================
    llm_generation_result = generate_llm_response(normalized_input)
    state["llm_generation_result"] = llm_generation_result

    if llm_generation_result["generation_success"] is False:
        return make_pipeline_failure(
            error_component="llm_response_generator",
            error_message=llm_generation_result.get("generation_error"),
            partial_state=state,
        )

    raw_llm_output = llm_generation_result["raw_llm_output"]
    state["raw_llm_output"] = raw_llm_output

    # ==================================================
    # Parser 2
    # ==================================================
    parser_2_result = parse_llm_response(raw_llm_output)
    state["parser_2_result"] = parser_2_result

    if parser_2_result["response_parse_success"] is False:
        return make_pipeline_failure(
            error_component="parser_2",
            error_message=parser_2_result.get("response_parse_error"),
            partial_state=state,
        )

    parsed_trace = parser_2_result["trace"]
    state["parsed_trace"] = parsed_trace

    # ==================================================
    # Translator
    # ==================================================
    translation_result = translate_problem_and_trace(
        parsed_problem=parsed_problem,
        parsed_trace=parsed_trace,
    )
    state["translation_result"] = translation_result

    if translation_result["translation_success"] is False:
        return make_pipeline_failure(
            error_component="translator",
            error_message=translation_result.get("translation_error"),
            partial_state=state,
        )

    symbolic_problem = translation_result["symbolic_problem"]
    symbolic_trace = translation_result["symbolic_trace"]

    state["symbolic_problem"] = symbolic_problem
    state["symbolic_trace"] = symbolic_trace

    # ==================================================
    # Verifier
    # ==================================================
    verification_result = verify_symbolic_trace(
        symbolic_problem=symbolic_problem,
        symbolic_trace=symbolic_trace,
    )
    state["verification_result"] = verification_result

    if verification_result["verification_success"] is False:
        return make_pipeline_failure(
            error_component="verifier",
            error_message=verification_result.get("verification_error"),
            partial_state=state,
        )

    return make_pipeline_success(state)


def run_pipeline_with_repair_inputs(
    raw_inputs: List[str],
    max_repair_attempts: int = MAX_REPAIR_ATTEMPTS,
) -> Dict[str, Any]:
    """
    Automated repair-loop runner.

    This is useful for tests.
    It receives a list of raw inputs:
    - first input = original attempt
    - next inputs = repaired attempts

    It does not ask the user interactively.
    """

    attempts = []
    total_allowed_inputs = max_repair_attempts + 1

    for attempt_index, raw_input in enumerate(raw_inputs[:total_allowed_inputs], start=1):
        result = run_full_pipeline_once(raw_input)

        attempts.append(
            {
                "attempt_number": attempt_index,
                "raw_input": raw_input,
                "result": result,
            }
        )

        if result["pipeline_success"] is True:
            return {
                "repair_loop_success": True,
                "repair_loop_status": "success",
                "attempts_used": attempt_index,
                "attempts": attempts,
                "final_pipeline_result": result,
                "final_error": None,
            }

        if attempt_index > max_repair_attempts:
            break

    final_result = attempts[-1]["result"] if attempts else None

    return {
        "repair_loop_success": False,
        "repair_loop_status": "failed",
        "attempts_used": len(attempts),
        "attempts": attempts,
        "final_pipeline_result": final_result,
        "final_error": final_result.get("error_message") if final_result else "No input attempts provided.",
    }


def run_interactive_repair_loop(
    initial_raw_input: str,
    input_provider: Callable[[str], str] = input,
    max_repair_attempts: int = MAX_REPAIR_ATTEMPTS,
) -> Dict[str, Any]:
    """
    Interactive global user-guided repair loop.

    Behavior:
    - Runs full pipeline.
    - If it fails, prints/returns a repair message.
    - Gets corrected raw input from the user.
    - Restarts from the Normalizer.
    """

    current_input = initial_raw_input
    attempts = []

    for attempt_number in range(1, max_repair_attempts + 2):
        result = run_full_pipeline_once(current_input)

        attempts.append(
            {
                "attempt_number": attempt_number,
                "raw_input": current_input,
                "result": result,
            }
        )

        if result["pipeline_success"] is True:
            return {
                "repair_loop_success": True,
                "repair_loop_status": "success",
                "attempts_used": attempt_number,
                "attempts": attempts,
                "final_pipeline_result": result,
                "final_error": None,
            }

        if attempt_number > max_repair_attempts:
            break

        repair_message = build_repair_message(
            error_component=result.get("error_component"),
            error_message=result.get("error_message"),
            repair_attempt=attempt_number,
            max_repair_attempts=max_repair_attempts,
        )

        print("\n" + "=" * 100)
        print("REPAIR LOOP")
        print("-" * 100)
        print(repair_message)
        print("=" * 100)

        current_input = input_provider("Corrected raw prompt: ")

    final_result = attempts[-1]["result"]

    return {
        "repair_loop_success": False,
        "repair_loop_status": "failed",
        "attempts_used": len(attempts),
        "attempts": attempts,
        "final_pipeline_result": final_result,
        "final_error": final_result.get("error_message"),
    }