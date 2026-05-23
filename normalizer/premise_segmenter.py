from typing import Any, Dict, List


ERROR_NO_CANDIDATE_PREMISES = "No candidate premises found"
ERROR_PREMISE_SEGMENTATION = "Candidate premises could not be separated using full stops"


def _make_failure(errors: List[str]) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors:
        if isinstance(error, str) and error.strip():
            clean_error = error.strip()
            if clean_error not in cleaned_errors:
                cleaned_errors.append(clean_error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_PREMISE_SEGMENTATION]

    return {
        "success": False,
        "premises": [],
        "normalized_input": None,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(premises: List[str]) -> Dict[str, Any]:
    return {
        "success": True,
        "premises": premises,
        "normalized_input": None,
        "errors": [],
        "error": None,
    }


def _split_by_full_stop(candidate_premise_text: str) -> List[str]:
    """
    Deterministically split candidate premise text into premise sentences.

    Since the input is assumed to be well-punctuated, each premise sentence
    must end with a full stop.

    Example:
        "ahmed studies. sara sleeps."
        ->
        ["ahmed studies.", "sara sleeps."]
    """

    premises = []
    current = []

    for char in candidate_premise_text:
        current.append(char)

        if char == ".":
            sentence = "".join(current).strip()
            current = []

            if sentence:
                premises.append(sentence)

    remaining = "".join(current).strip()

    if remaining:
        return []

    return premises


def build_normalized_prompt(premises: List[str], question: str) -> str:
    """
    Builds the normalized prompt format expected by the next pipeline component.

    Output format:
    Premises:
    1. ...
    2. ...

    Question:
    ...
    """

    normalized_output = "Premises:\n"

    for i, premise in enumerate(premises, start=1):
        normalized_output += f"{i}. {premise}\n"

    normalized_output += f"\nQuestion:\n{question.strip()}"

    return normalized_output


def segment_and_validate_premises(candidate_premise_text: str) -> Dict[str, Any]:
    """
    Normalizer Component N3: Premises Separator.

    Planned deterministic functionality:
    1. Receive candidate premise text from N2.
    2. If there is no remaining text, fail with:
       "No candidate premises found"
    3. Split the candidate premise text into premise sentences using full stops.
    4. Return the separated premises.

    Note:
    The normalized prompt is built separately using build_normalized_prompt(),
    because the question is produced by N2.
    """

    if candidate_premise_text is None:
        return _make_failure([ERROR_NO_CANDIDATE_PREMISES])

    if not isinstance(candidate_premise_text, str):
        return _make_failure([ERROR_PREMISE_SEGMENTATION])

    if not candidate_premise_text.strip():
        return _make_failure([ERROR_NO_CANDIDATE_PREMISES])

    premises = _split_by_full_stop(candidate_premise_text.strip())

    if not premises:
        return _make_failure([ERROR_PREMISE_SEGMENTATION])

    return _make_success(premises)