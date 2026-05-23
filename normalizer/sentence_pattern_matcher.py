from typing import Any, Dict, List

from normalizer.llm_utils import call_llm_json
from prompts.normalizer.sentence_pattern_match_prompt import SENTENCE_PATTERN_MATCH_PROMPT


ERROR_PATTERN_MATCH = "One or more premises do not map into supported sentence patterns"


def _make_failure(
    errors: List[str],
    failed_premises: List[str] | None = None,
) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors:
        if isinstance(error, str) and error.strip():
            clean_error = error.strip()
            if clean_error not in cleaned_errors:
                cleaned_errors.append(clean_error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_PATTERN_MATCH]

    cleaned_failed_premises = []

    for premise in failed_premises or []:
        if isinstance(premise, str) and premise.strip():
            clean_premise = premise.strip()
            if clean_premise not in cleaned_failed_premises:
                cleaned_failed_premises.append(clean_premise)

    return {
        "success": False,
        "pattern_matched_premises": [],
        "failed_premises": cleaned_failed_premises,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(pattern_matched_premises: List[str]) -> Dict[str, Any]:
    return {
        "success": True,
        "pattern_matched_premises": pattern_matched_premises,
        "failed_premises": [],
        "errors": [],
        "error": None,
    }


def _call_pattern_match_llm(premises: List[str]) -> Dict[str, Any]:
    user_prompt = {
        "premises": premises
    }

    return call_llm_json(SENTENCE_PATTERN_MATCH_PROMPT, str(user_prompt))


def _validate_result_shape(result: Any) -> Dict[str, Any] | None:
    if not isinstance(result, dict):
        return _make_failure([ERROR_PATTERN_MATCH])

    if "success" not in result or not isinstance(result["success"], bool):
        return _make_failure([ERROR_PATTERN_MATCH])

    if "pattern_matched_premises" not in result:
        return _make_failure([ERROR_PATTERN_MATCH])

    if "failed_premises" not in result:
        return _make_failure([ERROR_PATTERN_MATCH])

    if "errors" not in result:
        return _make_failure([ERROR_PATTERN_MATCH])

    if not isinstance(result["pattern_matched_premises"], list):
        return _make_failure([ERROR_PATTERN_MATCH])

    if not isinstance(result["failed_premises"], list):
        return _make_failure([ERROR_PATTERN_MATCH])

    if not isinstance(result["errors"], list):
        return _make_failure([ERROR_PATTERN_MATCH])

    if result["success"]:
        if result["errors"] != []:
            return _make_failure([ERROR_PATTERN_MATCH])

        if result["failed_premises"] != []:
            return _make_failure([ERROR_PATTERN_MATCH])

        if not result["pattern_matched_premises"]:
            return _make_failure([ERROR_PATTERN_MATCH])

        for premise in result["pattern_matched_premises"]:
            if not isinstance(premise, str) or not premise.strip():
                return _make_failure([ERROR_PATTERN_MATCH])

    else:
        if result["pattern_matched_premises"] != []:
            return _make_failure([ERROR_PATTERN_MATCH])

        if not result["errors"]:
            return _make_failure([ERROR_PATTERN_MATCH])

        if not result["failed_premises"]:
            return _make_failure([ERROR_PATTERN_MATCH])

        for premise in result["failed_premises"]:
            if not isinstance(premise, str) or not premise.strip():
                return _make_failure([ERROR_PATTERN_MATCH])

    return None


def match_sentence_patterns(premises: List[str]) -> Dict[str, Any]:
    if not isinstance(premises, list) or not premises:
        return _make_failure([ERROR_PATTERN_MATCH])

    for premise in premises:
        if not isinstance(premise, str) or not premise.strip():
            return _make_failure([ERROR_PATTERN_MATCH])

    try:
        result = _call_pattern_match_llm(premises)
    except Exception as e:
        return _make_failure([f"{ERROR_PATTERN_MATCH}: {e}"])

    shape_error = _validate_result_shape(result)
    if shape_error is not None:
        return shape_error

    if result["success"] is False:
        return _make_failure(
            result["errors"],
            failed_premises=result["failed_premises"],
        )

    return _make_success(result["pattern_matched_premises"])