from typing import Any, Dict


def unify_case(raw_input: str) -> Dict[str, Any]:
    """
    Normalizer Component N1: Case Unification.

    This component receives the raw user input and converts it fully to lowercase.

    It does not:
    - rewrite meaning
    - change punctuation
    - add punctuation
    - remove punctuation
    - call an LLM
    - validate questions
    - validate premises
    """

    if raw_input is None:
        return {
            "success": False,
            "case_unified_input": None,
            "error": "CASE_UNIFICATION_ERROR: Input is None",
            "debug": {
                "original_input": raw_input,
            },
        }

    case_unified_input = raw_input.lower()

    return {
        "success": True,
        "case_unified_input": case_unified_input,
        "error": None,
        "debug": {
            "original_input": raw_input,
            "case_unified_input": case_unified_input,
        },
    }