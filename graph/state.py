from typing import TypedDict, List, Dict, Any, Optional


class GraphState(TypedDict, total=False):
    # Input

    # Raw Input (NEW)
    raw_input: str

    # Normalization (NEW)
    normalized_input: Optional[str]
    normalization_success: Optional[bool]
    normalization_error: Optional[str]
    premises: List[str]
    question: str
    metadata: Dict[str, Any]
    normalized_input: Optional[str]
    normalization_success: Optional[bool]
    normalization_error: Optional[str]

    parsed_problem: Dict[str, Any]
    prompt_parse_success: bool
    prompt_parse_error: Optional[str]
    normalization_debug: Dict[str, Any]

    # Generation
    raw_llm_output: str

    # Parsing
    parsed_trace: Dict[str, Any]
    parse_success: bool
    parse_error: Optional[str]
    response_parse_success: bool
    response_parse_error: Optional[str]

    # Translation
    symbolic_premises: Dict[str, str]
    symbolic_question: Optional[str]
    symbolic_trace: Dict[str, Any]
    translation_success: bool
    translation_error: Optional[str]
    symbolic_problem: Dict[str, Any]

    # Verification
    verification_result: Dict[str, Any]
    verification_success: bool
    verification_error: Optional[str]

    # Control
    status: str
    failure_stage: Optional[str]

    # Final output
    final_result: Dict[str, Any]


def make_initial_state(
    raw_input: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> GraphState:
    return {
        "raw_input": raw_input,
        "metadata": metadata or {},
        "status": "initialized",
        "failure_stage": None,
    }