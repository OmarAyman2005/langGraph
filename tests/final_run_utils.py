import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from llm_response.llm_response_generator import generate_llm_response
from parsers.llm_response_parser import parse_llm_response
from translator.translator import translate_problem_and_trace
from verifier.verifier import verify_symbolic_trace


# ============================================================
# Pretty Printing Helpers
# ============================================================

def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def print_block(title: str) -> None:
    print("-" * 80)
    print(title)


def as_text(value: Any) -> str:
    if value is None:
        return "None"

    if isinstance(value, (dict, list)):
        return pretty_json(value)

    return str(value)


def timed_call(func, *args, **kwargs) -> Tuple[Any, int]:
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, int((end - start) * 1000)


def get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        if key not in current:
            return default

        current = current[key]

    return current


# ============================================================
# Error Code Mapping
# ============================================================

def map_normalizer_error(error_message: Optional[str]) -> Tuple[str, str]:
    """
    Returns:
    - failed_subcomponent
    - error_code
    """

    if not error_message:
        return "N/A", "N/A"

    error = error_message.lower()

    # N1
    if "empty input" in error:
        return "N1", "CA_EMPTY_INPUT"

    has_unsupported = "unsupported character" in error
    has_non_english = "non-english character" in error or "non english character" in error

    if has_unsupported and has_non_english:
        return "N1", "CA_UNSUPPORTED_CHARACTER + CA_NON_ENGLISH_CHARACTER"

    if has_unsupported:
        return "N1", "CA_UNSUPPORTED_CHARACTER"

    if has_non_english:
        return "N1", "CA_NON_ENGLISH_CHARACTER"

    # N2
    if "more than one yes/no question" in error:
        return "N2", "QD_MULTIPLE_YN_QUESTIONS"

    if "non yes/no question" in error or "non-yes/no question" in error:
        return "N2", "QD_NON_YN_QUESTION"

    if "no yes/no question" in error:
        return "N2", "QD_NO_YN_QUESTION"

    # N3
    if "no candidate premises" in error:
        return "N3", "PS_NO_CANDIDATE_PREMISES"

    if "premise" in error and "full stop" in error:
        return "N3", "PS_INVALID_PREMISE_SEGMENTATION"

    # N4
    if "premises do not map into supported sentence patterns" in error:
        return "N4", "SPM_UNSUPPORTED_SENTENCE_PATTERN"

    if "unsupported sentence pattern" in error:
        return "N4", "SPM_UNSUPPORTED_SENTENCE_PATTERN"

    # N5
    if "question target does not map" in error:
        return "N5", "QPM_UNSUPPORTED_QUESTION_PATTERN"

    if "unsupported question" in error:
        return "N5", "QPM_UNSUPPORTED_QUESTION_PATTERN"

    # N6
    if "ambiguous" in error and "subject" in error:
        return "N6", "SP_AMBIGUOUS_SUBJECT_PROPAGATION"

    return "Normalizer", "NORMALIZER_ERROR_UNMAPPED"


def map_verifier_error_code(verification_error: Any) -> str:
    if verification_error is None:
        return "None"

    if isinstance(verification_error, dict):
        return verification_error.get("error_code", "VF_UNKNOWN_ERROR")

    error = str(verification_error).lower()

    if "contradictory premises detected" in error:
        return "VF_CONTRADICTORY_PREMISES"

    if "closure safety" in error:
        return "VF_CLOSURE_LIMIT_EXCEEDED"

    if "unsupported rule implementation" in error:
        return "VF_UNSUPPORTED_RULE_IMPLEMENTATION"

    return "VF_MALFORMED_SYMBOLIC_INPUT"


# ============================================================
# Normalization Feature Count Helpers
# ============================================================

def split_sentences(raw_input: str) -> List[str]:
    """
    Simple sentence splitter used only for estimating case adjustment count.
    Keeps question sentences too.
    """

    pieces = re.split(r"(?<=[.?])\s+", raw_input.strip())
    return [p.strip() for p in pieces if p.strip()]


def estimate_case_adjustment_count(raw_input: str) -> int:
    """
    Option B definition:
    Number of sentences where case adjustment is needed, capped at 3.
    """

    count = 0

    for sentence in split_sentences(raw_input):
        if any(ch.isalpha() and ch.isupper() for ch in sentence):
            count += 1

    return min(count, 3)


def extract_change_count(debug_obj: Any) -> int:
    """
    Generic helper for debug objects that contain a 'changes' list.
    """

    if not isinstance(debug_obj, dict):
        return 0

    changes = debug_obj.get("changes")

    if isinstance(changes, list):
        return len(changes)

    return 0


def get_normalizer_debug(normalizer_result: Dict[str, Any]) -> Dict[str, Any]:
    debug = normalizer_result.get("debug")
    return debug if isinstance(debug, dict) else {}


def get_normalized_prompt_or_null(normalizer_result: Dict[str, Any]) -> Any:
    if normalizer_result.get("success") is True:
        return normalizer_result.get("normalized_input")
    return None


def calculate_actual_normalization_counts(
    raw_input: str,
    normalizer_result: Dict[str, Any],
) -> Dict[str, int]:
    """
    Best-effort extraction from normalizer debug.
    If some debug keys are absent, the corresponding count becomes 0.
    """

    debug = get_normalizer_debug(normalizer_result)

    case_count = estimate_case_adjustment_count(raw_input)

    # These keys are based on your current debug style from previous tests.
    # If your normalizer exposes different names later, only update this mapping.
    pattern_count = extract_change_count(debug.get("n4_sentence_pattern_matcher"))
    subject_count = extract_change_count(debug.get("n6_subject_propagator"))
    synonym_count = extract_change_count(debug.get("n7_synonym_words_unifier"))
    antonym_count = extract_change_count(debug.get("n8_antonym_words_unifier"))

    total = case_count + pattern_count + subject_count + synonym_count + antonym_count

    return {
        "case": case_count,
        "pattern": pattern_count,
        "subject": subject_count,
        "synonym": synonym_count,
        "antonym": antonym_count,
        "total": total,
    }


def get_triggered(value: int) -> str:
    return "Yes" if value > 0 else "No"


def get_output_or_not_modified(triggered: str, output: Any) -> str:
    if triggered == "Yes":
        return as_text(output)
    return "Was Not Modified"


# ============================================================
# Subcomponent Trace Printing
# ============================================================

def print_score_component_trace(
    name: str,
    status: str,
    triggered: str,
    count_label: str,
    count_value: int,
    output: Any,
    error_code: str,
    error_message: str,
    runtime_ms: int,
) -> None:
    print(f"{name}:")
    print(f"  Status: {status}")
    print(f"  Triggered: {triggered}")
    print(f"  {count_label}: {count_value}")
    print("  Output_After_Component:")
    print(f"  {get_output_or_not_modified(triggered, output)}")
    print(f"  Error_Code: {error_code}")
    print(f"  Error_Message: {error_message}")
    print(f"  Runtime_ms: {runtime_ms}")
    print()


def print_non_score_component_trace(
    name: str,
    status: str,
    output: Any,
    error_code: str,
    error_message: str,
    runtime_ms: int,
) -> None:
    print(f"{name}:")
    print(f"  Status: {status}")
    print("  Output_After_Component:")
    print(f"  {as_text(output)}")
    print(f"  Error_Code: {error_code}")
    print(f"  Error_Message: {error_message}")
    print(f"  Runtime_ms: {runtime_ms}")
    print()


def extract_question_from_normalized_prompt(normalized_prompt: Any) -> str:
    if not isinstance(normalized_prompt, str):
        return "N/A"

    if "Question:" not in normalized_prompt:
        return "N/A"

    question_part = normalized_prompt.split("Question:", 1)[1].strip()
    return question_part if question_part else "N/A"


def extract_premises_text_from_normalized_prompt(normalized_prompt: Any) -> str:
    if not isinstance(normalized_prompt, str):
        return "N/A"

    if "Premises:" not in normalized_prompt or "Question:" not in normalized_prompt:
        return "N/A"

    premises_part = normalized_prompt.split("Premises:", 1)[1].split("Question:", 1)[0].strip()
    return premises_part if premises_part else "N/A"

def print_normalizer_section(
    raw_input: str,
    normalizer_result: Dict[str, Any],
    normalizer_runtime_ms: int,
) -> Dict[str, Any]:
    """
    Prints the final terminal format for the normalizer section.
    Returns useful summary values.
    """

    debug = get_normalizer_debug(normalizer_result)
    counts = calculate_actual_normalization_counts(raw_input, normalizer_result)

    normalizer_success = normalizer_result.get("success") is True
    error_message = normalizer_result.get("error") if not normalizer_success else None
    failed_subcomponent, error_code = map_normalizer_error(error_message)

    print_block("[COMPONENT 1: NORMALIZER]")
    print(f"Status: {'success' if normalizer_success else 'failed'}")
    print()
    print("[NORMALIZER SUBCOMPONENT TRACE]")
    print()

    # Approximate status cascade.
    subcomponents = ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"]

    def component_status(component_id: str) -> str:
        if normalizer_success:
            return "success"

        if failed_subcomponent == component_id:
            return "failed"

        if failed_subcomponent in subcomponents:
            failed_index = subcomponents.index(failed_subcomponent)
            current_index = subcomponents.index(component_id)

            if current_index < failed_index:
                return "success"

            if current_index > failed_index:
                return "skipped"

        return "skipped"

    def component_error(component_id: str) -> Tuple[str, str]:
        if failed_subcomponent == component_id:
            return error_code, error_message or "Unknown error."
        if component_status(component_id) == "skipped":
            return "N/A", "N/A"
        return "None", "None"

    normalized_prompt = get_normalized_prompt_or_null(normalizer_result)

    case_unified_input = raw_input.lower()

    detected_question = extract_question_from_normalized_prompt(normalized_prompt)
    candidate_premises_text = extract_premises_text_from_normalized_prompt(normalized_prompt)

    n2_output = "null"
    n3_output = "null"
    n5_output = "null"

    if normalizer_success:
        n2_output = (
            "Candidate_Premises_Text:\n"
            f"{candidate_premises_text}\n\n"
            "Detected_Question:\n"
            f"{detected_question}"
        )

        n3_output = normalized_prompt if normalized_prompt is not None else "N/A"

        n5_output = (
            "Question:\n"
            f"{detected_question}"
        )
    else:
        if failed_subcomponent not in {"N1", "N2"}:
            n2_output = (
                "Candidate_Premises_Text:\n"
                f"{candidate_premises_text}\n\n"
                "Detected_Question:\n"
                f"{detected_question}"
            )

        if failed_subcomponent not in {"N1", "N2", "N3"}:
            n3_output = normalized_prompt if normalized_prompt is not None else "N/A"

        if failed_subcomponent not in {"N1", "N2", "N3", "N4", "N5"}:
            n5_output = (
                "Question:\n"
                f"{detected_question}"
            )

    # N1
    n1_status = component_status("N1")
    n1_triggered = "N/A" if n1_status == "skipped" else get_triggered(counts["case"])
    n1_error_code, n1_error_message = component_error("N1")
    print_score_component_trace(
        name="N1_Character_Adjuster",
        status=n1_status,
        triggered=n1_triggered,
        count_label="Actual_Case_Adjustment_Count",
        count_value=counts["case"] if n1_status != "skipped" else 0,
        output=raw_input.lower(),
        error_code=n1_error_code,
        error_message=n1_error_message,
        runtime_ms=0,
    )

    # N2
    n2_status = component_status("N2")
    n2_error_code, n2_error_message = component_error("N2")
    print_non_score_component_trace(
        name="N2_Question_Detector",
        status=n2_status,
        output=n2_output if n2_status == "success" else ("null" if n2_status == "failed" else "skipped_due_to_previous_failure"),
        error_code=n2_error_code,
        error_message=n2_error_message,
        runtime_ms=0,
    )

    # N3
    n3_status = component_status("N3")
    n3_error_code, n3_error_message = component_error("N3")
    print_non_score_component_trace(
        name="N3_Premise_Segmenter",
        status=n3_status,
        output=n3_output if n3_status == "success" else ("null" if n3_status == "failed" else "skipped_due_to_previous_failure"),
        error_code=n3_error_code,
        error_message=n3_error_message,
        runtime_ms=0,
    )

    # N4
    n4_status = component_status("N4")
    n4_triggered = "N/A" if n4_status == "skipped" else get_triggered(counts["pattern"])
    n4_error_code, n4_error_message = component_error("N4")
    print_score_component_trace(
        name="N4_Sentence_Pattern_Matcher",
        status=n4_status,
        triggered=n4_triggered,
        count_label="Actual_Pattern_Rewrite_Count",
        count_value=counts["pattern"] if n4_status != "skipped" else 0,
        output=debug.get("normalized_prompt_after_n4", "See normalizer debug."),
        error_code=n4_error_code,
        error_message=n4_error_message,
        runtime_ms=0,
    )

    # N5
    n5_status = component_status("N5")
    n5_error_code, n5_error_message = component_error("N5")
    print_non_score_component_trace(
        name="N5_Question_Pattern_Matcher",
        status=n5_status,
        output=n5_output if n5_status == "success" else ("null" if n5_status == "failed" else "skipped_due_to_previous_failure"),
        error_code=n5_error_code,
        error_message=n5_error_message,
        runtime_ms=0,
    )

    # N6
    n6_status = component_status("N6")
    n6_triggered = "N/A" if n6_status == "skipped" else get_triggered(counts["subject"])
    n6_error_code, n6_error_message = component_error("N6")
    print_score_component_trace(
        name="N6_Subject_Propagator",
        status=n6_status,
        triggered=n6_triggered,
        count_label="Actual_Subject_Propagation_Count",
        count_value=counts["subject"] if n6_status != "skipped" else 0,
        output=debug.get("normalized_prompt_after_n6", "See normalizer debug."),
        error_code=n6_error_code,
        error_message=n6_error_message,
        runtime_ms=0,
    )

    # N7
    n7_status = component_status("N7")
    n7_triggered = "N/A" if n7_status == "skipped" else get_triggered(counts["synonym"])
    n7_error_code, n7_error_message = component_error("N7")
    print_score_component_trace(
        name="N7_Synonym_Words_Unifier",
        status=n7_status,
        triggered=n7_triggered,
        count_label="Actual_Synonym_Unification_Count",
        count_value=counts["synonym"] if n7_status != "skipped" else 0,
        output=debug.get("normalized_prompt_after_n7", "See normalizer debug."),
        error_code=n7_error_code,
        error_message=n7_error_message,
        runtime_ms=0,
    )

    # N8
    n8_status = component_status("N8")
    n8_triggered = "N/A" if n8_status == "skipped" else get_triggered(counts["antonym"])
    n8_error_code, n8_error_message = component_error("N8")
    print_score_component_trace(
        name="N8_Antonym_Words_Unifier",
        status=n8_status,
        triggered=n8_triggered,
        count_label="Actual_Antonym_Unification_Count",
        count_value=counts["antonym"] if n8_status != "skipped" else 0,
        output=debug.get("final_normalized_prompt_after_n8", normalized_prompt if normalized_prompt else "See normalizer debug."),
        error_code=n8_error_code,
        error_message=n8_error_message,
        runtime_ms=0,
    )

    print("[NORMALIZER FINAL SUMMARY]")
    print(f"Normalizer_Status: {'success' if normalizer_success else 'failed'}")
    print(f"Failed_Normalizer_SubComponent: {failed_subcomponent if not normalizer_success else 'None'}")
    print(f"Normalizer_Error_Code: {error_code if not normalizer_success else 'None'}")
    print(f"Normalizer_Error_Message: {error_message if not normalizer_success else 'None'}")
    print()
    print("Triggered_Normalization_Features:")
    print(f"Actual_Case_Adjustment_Count: {counts['case']}")
    print(f"Actual_Pattern_Rewrite_Count: {counts['pattern']}")
    print(f"Actual_Subject_Propagation_Count: {counts['subject']}")
    print(f"Actual_Synonym_Unification_Count: {counts['synonym']}")
    print(f"Actual_Antonym_Unification_Count: {counts['antonym']}")
    print(f"Actual_Normalization_Complexity_Score: {counts['total']}")
    print()
    print("Normalized_Prompt:")
    print(as_text(normalized_prompt))
    print()
    print(f"Normalizer_Runtime_ms: {normalizer_runtime_ms}")
    print()

    return {
        "success": normalizer_success,
        "failed_subcomponent": failed_subcomponent if not normalizer_success else None,
        "error_code": error_code if not normalizer_success else None,
        "error_message": error_message,
        "runtime_ms": normalizer_runtime_ms,
        "counts": counts,
        "normalized_prompt": normalized_prompt,
    }


# ============================================================
# Verifier Summary Helpers
# ============================================================

def summarize_verifier_output(verification_output: Dict[str, Any]) -> Dict[str, str]:
    if verification_output.get("verification_success") is not True:
        error_code = map_verifier_error_code(verification_output.get("verification_error"))

        return {
            "steps_correctness": "N/A",
            "invalid_steps_reasons": "N/A",
            "not_entailed_reason": "N/A",
            "final_answer_consistency": "N/A",
            "final_validity": "N/A",
            "verifier_error": error_code,
        }

    result = verification_output.get("verification_result") or {}
    step_results = result.get("step_results") or []

    failed_steps = [
        step for step in step_results
        if step.get("valid") is False
    ]

    if not step_results:
        steps_correctness = "N/A"
        invalid_reasons = "None"
    elif not failed_steps:
        steps_correctness = "All Correct"
        invalid_reasons = "None"
    else:
        failed_ids = [step.get("id", "UNKNOWN") for step in failed_steps]
        steps_correctness = "Failed: " + ", ".join(failed_ids)
        invalid_reasons = "; ".join(
            f"{step.get('id', 'UNKNOWN')}: {step.get('error', 'UNKNOWN')}"
            for step in failed_steps
        )

    return {
        "steps_correctness": steps_correctness,
        "invalid_steps_reasons": invalid_reasons,
        "not_entailed_reason": result.get("not_entailed_reason", "N/A"),
        "final_answer_consistency": result.get("final_answer_check", "N/A"),
        "final_validity": result.get("validity", "N/A"),
        "verifier_error": "None",
    }


# ============================================================
# Metadata Printing
# ============================================================

D1_FIELDS = [
    "Expected_Entailment_Status",
    "Expected_Not_Entailed_Type",
    "Inference_Depth",
    "Inference_Rules",
    "Distractor_Count",
    "Case_Adjustment_Count",
    "Pattern_Rewrite_Count",
    "Subject_Propagation_Count",
    "Synonym_Unification_Count",
    "Antonym_Unification_Count",
    "Normalization_Complexity_Score",
]

D2_FIELDS = [
    "Expected_Component",
    "Expected_SubComponent",
    "Expected_Specific_Error",
]


def get_meta(example: Dict[str, Any], field: str) -> Any:
    return example.get(field, "N/A")


def print_dataset_metadata(example: Dict[str, Any]) -> None:
    print_block("[DATASET METADATA — D1]")
    for field in D1_FIELDS:
        print(f"{field}: {get_meta(example, field)}")
    print()

    print("[DATASET METADATA — D2]")
    for field in D2_FIELDS:
        print(f"{field}: {get_meta(example, field)}")
    print()


# ============================================================
# Component Skip Printers
# ============================================================

def print_parser1_skipped() -> None:
    print_block("[COMPONENT 2: NORMALIZED PROMPT PARSER]")
    print("Status: skipped")
    print()
    print("Parsed_Normalized_Prompt:")
    print("null")
    print()
    print("Prompt_Parser_Error: N/A")
    print("Runtime_ms: 0")
    print()


def print_llm_skipped() -> None:
    print_block("[COMPONENT 3: LLM REASONING MODULE]")
    print("Status: skipped")
    print()
    print("LLM_Model: N/A")
    print("LLM_Temperature: N/A")
    print()
    print("LLM_Response:")
    print("null")
    print()
    print("LLM_Response_Error: N/A")
    print("Runtime_ms: 0")
    print()


def print_parser2_skipped() -> None:
    print_block("[COMPONENT 4: LLM RESPONSE PARSER]")
    print("Status: skipped")
    print()
    print("Parsed_LLM_Response:")
    print("null")
    print()
    print("LLM_Response_Parser_Error: N/A")
    print("Runtime_ms: 0")
    print()


def print_translator_skipped() -> None:
    print_block("[COMPONENT 5: TRANSLATOR]")
    print("Status: skipped")
    print()
    print("Symbolic_Translation:")
    print("null")
    print()
    print("Translator_Error: N/A")
    print("Runtime_ms: 0")
    print()


def print_verifier_skipped() -> None:
    print_block("[COMPONENT 6: VERIFIER]")
    print("Status: skipped")
    print()
    print("Verifier_Output:")
    print("null")
    print()
    print("Steps_Correctness: N/A")
    print("Invalid_Steps_Reasons: N/A")
    print("Not_Entailed_Reason: N/A")
    print("Final_Answer_Consistency: N/A")
    print("Final_Validity: N/A")
    print("Verifier_Error: N/A")
    print("Runtime_ms: 0")
    print()


def print_skipped_after_normalizer() -> None:
    print_parser1_skipped()
    print_llm_skipped()
    print_parser2_skipped()
    print_translator_skipped()
    print_verifier_skipped()


def print_skipped_after_parser1() -> None:
    print_llm_skipped()
    print_parser2_skipped()
    print_translator_skipped()
    print_verifier_skipped()


def print_skipped_after_llm() -> None:
    print_parser2_skipped()
    print_translator_skipped()
    print_verifier_skipped()


def print_skipped_after_parser2() -> None:
    print_translator_skipped()
    print_verifier_skipped()


def print_skipped_after_translator() -> None:
    print_verifier_skipped()


# ============================================================
# Main Single Run Function
# ============================================================

def run_and_print_example(
    example: Dict[str, Any],
    include_dataset_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Runs one example and prints the exact designed terminal output.
    """

    example_id = example.get("Example_ID", "UNKNOWN_EXAMPLE")
    dataset_type = example.get("Dataset_Type", "UNKNOWN_DATASET")
    run_id = example.get("Run_ID", 1)
    raw_input = example.get("Raw_Input", "")

    component_times = {
        "normalization": 0,
        "prompt_parsing": 0,
        "llm_response": 0,
        "llm_response_parsing": 0,
        "translation": 0,
        "verification": 0,
    }

    pipeline_status = "failed"
    explanation_validity = "N/A"
    error_component = "None"
    error_message = "None"

    print("=" * 80)
    print("RUN START")
    print("=" * 80)
    print()
    print(f"Example_ID: {example_id}")
    print(f"Dataset_Type: {dataset_type}")
    print(f"Run_ID: {run_id}")
    print()
    print("[RAW INPUT]")
    print(raw_input)
    print()

    if include_dataset_metadata:
        print_dataset_metadata(example)

    # ==================================================
    # Component 1: Normalizer
    # ==================================================
    normalizer_result, normalizer_ms = timed_call(normalize_raw_prompt, raw_input)
    component_times["normalization"] = normalizer_ms

    normalizer_summary = print_normalizer_section(
        raw_input=raw_input,
        normalizer_result=normalizer_result,
        normalizer_runtime_ms=normalizer_ms,
    )

    if normalizer_summary["success"] is not True:
        print_skipped_after_normalizer()

        error_component = "Normalizer"
        error_message = normalizer_summary["error_code"] or "Normalizer failure"

        print_final_runtime_decision(
            pipeline_status=pipeline_status,
            explanation_validity=explanation_validity,
            error_component=error_component,
            error_message=error_message,
            component_times=component_times,
        )

        return {
            "pipeline_status": pipeline_status,
            "explanation_validity": explanation_validity,
            "error_component": error_component,
            "error_message": error_message,
        }

    normalized_prompt = normalizer_summary["normalized_prompt"]

    # ==================================================
    # Component 2: Parser 1
    # ==================================================
    parser1_result, parser1_ms = timed_call(parse_normalized_prompt, normalized_prompt)
    component_times["prompt_parsing"] = parser1_ms

    print_block("[COMPONENT 2: NORMALIZED PROMPT PARSER]")

    if parser1_result.get("prompt_parse_success") is False:
        print("Status: failed")
        print()
        print("Parsed_Normalized_Prompt:")
        print("null")
        print()
        print(f"Prompt_Parser_Error: {parser1_result.get('prompt_parse_error')}")
        print(f"Runtime_ms: {parser1_ms}")
        print()

        print_skipped_after_parser1()

        error_component = "Prompt_Parser"
        error_message = parser1_result.get("prompt_parse_error") or "Parser 1 failure"

        print_final_runtime_decision(
            pipeline_status=pipeline_status,
            explanation_validity=explanation_validity,
            error_component=error_component,
            error_message=error_message,
            component_times=component_times,
        )

        return {
            "pipeline_status": pipeline_status,
            "explanation_validity": explanation_validity,
            "error_component": error_component,
            "error_message": error_message,
        }

    print("Status: success")
    print()
    print("Parsed_Normalized_Prompt:")
    print(pretty_json(parser1_result.get("problem")))
    print()
    print("Prompt_Parser_Error: None")
    print(f"Runtime_ms: {parser1_ms}")
    print()

    parsed_problem = parser1_result["problem"]

    # ==================================================
    # Component 3: LLM
    # ==================================================
    llm_result, llm_ms = timed_call(generate_llm_response, normalized_prompt)
    component_times["llm_response"] = llm_ms

    print_block("[COMPONENT 3: LLM REASONING MODULE]")

    if llm_result.get("generation_success") is False:
        print("Status: failed")
        print()
        print(f"LLM_Model: {llm_result.get('model', 'N/A')}")
        print(f"LLM_Temperature: {llm_result.get('temperature', 'N/A')}")
        print()
        print("LLM_Response:")
        print("null")
        print()
        print(f"LLM_Response_Error: {llm_result.get('generation_error')}")
        print(f"Runtime_ms: {llm_ms}")
        print()

        print_skipped_after_llm()

        error_component = "LLM_Response_Generator"
        error_message = llm_result.get("generation_error") or "LLM generation failure"

        print_final_runtime_decision(
            pipeline_status=pipeline_status,
            explanation_validity=explanation_validity,
            error_component=error_component,
            error_message=error_message,
            component_times=component_times,
        )

        return {
            "pipeline_status": pipeline_status,
            "explanation_validity": explanation_validity,
            "error_component": error_component,
            "error_message": error_message,
        }

    raw_llm_output = llm_result.get("raw_llm_output")

    print("Status: success")
    print()
    print(f"LLM_Model: {llm_result.get('model', 'llama3.1:8b')}")
    print(f"LLM_Temperature: {llm_result.get('temperature', 0)}")
    print()
    print("LLM_Response:")
    print(raw_llm_output)
    print()
    print("LLM_Response_Error: None")
    print(f"Runtime_ms: {llm_ms}")
    print()

    # ==================================================
    # Component 4: Parser 2
    # ==================================================
    parser2_result, parser2_ms = timed_call(parse_llm_response, raw_llm_output)
    component_times["llm_response_parsing"] = parser2_ms

    print_block("[COMPONENT 4: LLM RESPONSE PARSER]")

    if parser2_result.get("response_parse_success") is False:
        print("Status: failed")
        print()
        print("Parsed_LLM_Response:")
        print("null")
        print()
        print(f"LLM_Response_Parser_Error: {parser2_result.get('response_parse_error')}")
        print(f"Runtime_ms: {parser2_ms}")
        print()

        print_skipped_after_parser2()

        error_component = "LLM_Response_Parser"
        error_message = parser2_result.get("response_parse_error") or "Parser 2 failure"

        print_final_runtime_decision(
            pipeline_status=pipeline_status,
            explanation_validity=explanation_validity,
            error_component=error_component,
            error_message=error_message,
            component_times=component_times,
        )

        return {
            "pipeline_status": pipeline_status,
            "explanation_validity": explanation_validity,
            "error_component": error_component,
            "error_message": error_message,
        }

    parsed_trace = parser2_result["trace"]

    print("Status: success")
    print()
    print("Parsed_LLM_Response:")
    print(pretty_json(parsed_trace))
    print()
    print("LLM_Response_Parser_Error: None")
    print(f"Runtime_ms: {parser2_ms}")
    print()

    # ==================================================
    # Component 5: Translator
    # ==================================================
    translation_result, translation_ms = timed_call(
        translate_problem_and_trace,
        parsed_problem=parsed_problem,
        parsed_trace=parsed_trace,
    )
    component_times["translation"] = translation_ms

    print_block("[COMPONENT 5: TRANSLATOR]")

    if translation_result.get("translation_success") is False:
        print("Status: failed")
        print()
        print("Symbolic_Translation:")
        print("null")
        print()
        print(f"Translator_Error: {translation_result.get('translation_error')}")
        print(f"Runtime_ms: {translation_ms}")
        print()

        print_skipped_after_translator()

        error_component = "Translator"
        error_message = translation_result.get("translation_error") or "Translator failure"

        print_final_runtime_decision(
            pipeline_status=pipeline_status,
            explanation_validity=explanation_validity,
            error_component=error_component,
            error_message=error_message,
            component_times=component_times,
        )

        return {
            "pipeline_status": pipeline_status,
            "explanation_validity": explanation_validity,
            "error_component": error_component,
            "error_message": error_message,
        }

    symbolic_translation = {
        "symbolic_problem": translation_result.get("symbolic_problem"),
        "symbolic_trace": translation_result.get("symbolic_trace"),
        "proposition_map": translation_result.get("proposition_map"),
    }

    print("Status: success")
    print()
    print("Symbolic_Translation:")
    print(pretty_json(symbolic_translation))
    print()
    print("Translator_Error: None")
    print(f"Runtime_ms: {translation_ms}")
    print()

    # ==================================================
    # Component 6: Verifier
    # ==================================================
    verification_output, verification_ms = timed_call(
        verify_symbolic_trace,
        symbolic_problem=translation_result["symbolic_problem"],
        symbolic_trace=translation_result["symbolic_trace"],
    )
    component_times["verification"] = verification_ms

    verifier_summary = summarize_verifier_output(verification_output)

    print_block("[COMPONENT 6: VERIFIER]")

    if verification_output.get("verification_success") is False:
        print("Status: failed")
    else:
        print("Status: success")

    print()
    print("Verifier_Output:")
    print(pretty_json(verification_output))
    print()
    print(f"Steps_Correctness: {verifier_summary['steps_correctness']}")
    print(f"Invalid_Steps_Reasons: {verifier_summary['invalid_steps_reasons']}")
    print(f"Not_Entailed_Reason: {verifier_summary['not_entailed_reason']}")
    print(f"Final_Answer_Consistency: {verifier_summary['final_answer_consistency']}")
    print(f"Final_Validity: {verifier_summary['final_validity']}")
    print(f"Verifier_Error: {verifier_summary['verifier_error']}")
    print(f"Runtime_ms: {verification_ms}")
    print()

    if verification_output.get("verification_success") is False:
        pipeline_status = "failed"
        explanation_validity = "N/A"
        error_component = "Verifier"
        error_message = verifier_summary["verifier_error"]
    else:
        pipeline_status = "success"
        explanation_validity = verifier_summary["final_validity"]
        error_component = "None"
        error_message = "None"

    print_final_runtime_decision(
        pipeline_status=pipeline_status,
        explanation_validity=explanation_validity,
        error_component=error_component,
        error_message=error_message,
        component_times=component_times,
    )

    return {
        "pipeline_status": pipeline_status,
        "explanation_validity": explanation_validity,
        "error_component": error_component,
        "error_message": error_message,
    }


def print_final_runtime_decision(
    pipeline_status: str,
    explanation_validity: str,
    error_component: str,
    error_message: str,
    component_times: Dict[str, int],
) -> None:
    total_runtime = sum(component_times.values())

    print_block("[FINAL RUNTIME DECISION]")
    print(f"Pipeline_Status: {pipeline_status}")
    print(f"Explanation_Validity: {explanation_validity}")
    print(f"Error_Component: {error_component}")
    print(f"Error_Message: {error_message}")
    print()

    print_block("[TIMING SUMMARY]")
    print(f"Normalization_Time_ms: {component_times['normalization']}")
    print(f"Prompt_Parsing_Time_ms: {component_times['prompt_parsing']}")
    print(f"LLM_Response_Time_ms: {component_times['llm_response']}")
    print(f"LLM_Response_Parsing_Time_ms: {component_times['llm_response_parsing']}")
    print(f"Translation_Time_ms: {component_times['translation']}")
    print(f"Verification_Time_ms: {component_times['verification']}")
    print(f"Total_Runtime_ms: {total_runtime}")
    print()

    print("=" * 80)
    print("RUN END")
    print("=" * 80)
    print()