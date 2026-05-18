from typing import Any, Dict, List

from prompts import PREMISE_SEGMENTATION_PROMPT
from normalizer.llm_utils import call_llm_json


def _make_failure(errors: List[str]) -> Dict[str, Any]:
    """
    Standard failure output for the premise separation component.
    """
    cleaned_errors = []

    for error in errors:
        if isinstance(error, str) and error.strip():
            cleaned_errors.append(error.strip())

    if not cleaned_errors:
        cleaned_errors = ["Premise separation failed"]

    return {
        "success": False,
        "premises": [],
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(premises: List[str]) -> Dict[str, Any]:
    """
    Standard success output for the premise separation component.
    """
    return {
        "success": True,
        "premises": premises,
        "errors": [],
        "error": None,
    }


def _basic_no_rest_check(candidate_premise_text: str) -> Dict[str, Any] | None:
    """
    Deterministic check for the no-rest case before calling the LLM.
    """
    if not candidate_premise_text or not candidate_premise_text.strip():
        return _make_failure(["No candidate premises found"])

    return None


def segment_premises_with_llm(candidate_premise_text: str) -> Dict[str, Any]:
    """
    Ask the LLM to separate candidate premise text into premise sentences
    and validate that each separated premise is a complete proper English sentence.
    """
    user_prompt = f"""Candidate premise text:
{candidate_premise_text}
"""
    return call_llm_json(PREMISE_SEGMENTATION_PROMPT, user_prompt)


def _validate_llm_result_shape(result: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Validate that the LLM returned the exact expected JSON shape.
    """
    if not isinstance(result, dict):
        return _make_failure(["Premise separation did not return a valid JSON object"])

    if "success" not in result:
        return _make_failure(["Premise separation result missing success field"])

    if not isinstance(result["success"], bool):
        return _make_failure(["Premise separation success field must be boolean"])

    if "premises" not in result:
        return _make_failure(["Premise separation result missing premises field"])

    if "errors" not in result:
        return _make_failure(["Premise separation result missing errors field"])

    if not isinstance(result["premises"], list):
        return _make_failure(["Premise separation premises field must be a list"])

    if not isinstance(result["errors"], list):
        return _make_failure(["Premise separation errors field must be a list"])

    if result["success"] is True:
        if result["errors"] != []:
            return _make_failure(
                ["Premise separation success output must have empty errors list"]
            )

        if not result["premises"]:
            return _make_failure(
                ["Premise separation success output must include at least one premise"]
            )

        for premise in result["premises"]:
            if not isinstance(premise, str) or not premise.strip():
                return _make_failure(
                    ["Premise separation returned an empty or invalid premise"]
                )

    if result["success"] is False:
        if result["premises"] != []:
            return _make_failure(
                ["Premise separation failure output must have empty premises list"]
            )

        if not result["errors"]:
            return _make_failure(
                ["Premise separation failure output must include at least one error"]
            )

        for error in result["errors"]:
            if not isinstance(error, str) or not error.strip():
                return _make_failure(
                    ["Premise separation returned an empty or invalid error"]
                )

    return None


def segment_and_validate_premises(candidate_premise_text: str) -> Dict[str, Any]:
    """
    Main public function for Normalizer Mini-Task 2.

    Input:
        candidate_premise_text:
            Candidate premise text to be separated and validated.

    Output:
        {
            "success": True,
            "premises": [...],
            "errors": [],
            "error": None
        }

        OR

        {
            "success": False,
            "premises": [],
            "errors": [...],
            "error": "<errors joined by newline>"
        }
    """
    no_rest_error = _basic_no_rest_check(candidate_premise_text)
    if no_rest_error is not None:
        return no_rest_error

    try:
        result = segment_premises_with_llm(candidate_premise_text.strip())
    except Exception as e:
        return _make_failure([f"Premise separation LLM call failed: {e}"])

    shape_error = _validate_llm_result_shape(result)
    if shape_error is not None:
        return shape_error

    if result["success"] is False:
        return _make_failure(result["errors"])

    return _make_success(result["premises"])
