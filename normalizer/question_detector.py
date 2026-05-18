import re
from typing import Any, Dict, List

from normalizer.llm_utils import call_llm_json
from prompts import QUESTION_DETECTION_PROMPT


ERROR_NO_YES_NO = "No yes/no question detected"
ERROR_MORE_THAN_ONE_YES_NO = "More than one yes/no question detected"
ERROR_NON_YES_NO = "Non yes/no question detected"

ALLOWED_ERRORS = {
    ERROR_NO_YES_NO,
    ERROR_MORE_THAN_ONE_YES_NO,
    ERROR_NON_YES_NO,
}


def _make_failure(errors: List[str]) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors:
        if isinstance(error, str) and error.strip() and error in ALLOWED_ERRORS:
            if error not in cleaned_errors:
                cleaned_errors.append(error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_NO_YES_NO]

    return {
        "success": False,
        "question": None,
        "candidate_premise_text": None,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(question: str, candidate_premise_text: str) -> Dict[str, Any]:
    return {
        "success": True,
        "question": question.strip(),
        "candidate_premise_text": candidate_premise_text.strip(),
        "errors": [],
        "error": None,
    }


def _call_question_detection_llm(raw_input: str) -> Dict[str, Any]:
    user_prompt = f"""Input:
{raw_input}
"""
    return call_llm_json(QUESTION_DETECTION_PROMPT, user_prompt)


def _normalize_llm_result(result: Any) -> Dict[str, Any]:
    """
    Normalizes the LLM JSON output into a predictable structure.
    N2 itself must only expose N2-specific errors.
    """
    if not isinstance(result, dict):
        return {
            "success": False,
            "yes_no_questions": [],
            "non_yes_no_questions": [],
            "errors": [ERROR_NO_YES_NO],
        }

    yes_no_questions = result.get("yes_no_questions", [])
    non_yes_no_questions = result.get("non_yes_no_questions", [])
    errors = result.get("errors", [])

    if not isinstance(yes_no_questions, list):
        yes_no_questions = []

    if not isinstance(non_yes_no_questions, list):
        non_yes_no_questions = []

    if not isinstance(errors, list):
        errors = []

    cleaned_yes_no_questions = []
    for item in yes_no_questions:
        if not isinstance(item, dict):
            continue

        text = item.get("text")

        if isinstance(text, str) and text.strip():
            cleaned_yes_no_questions.append({"text": text.strip()})

    cleaned_non_yes_no_questions = []
    for item in non_yes_no_questions:
        if not isinstance(item, dict):
            continue

        text = item.get("text")

        if isinstance(text, str) and text.strip():
            cleaned_non_yes_no_questions.append({"text": text.strip()})

    cleaned_errors = []
    for error in errors:
        if isinstance(error, str) and error.strip() in ALLOWED_ERRORS:
            if error.strip() not in cleaned_errors:
                cleaned_errors.append(error.strip())

    return {
        "success": len(cleaned_errors) == 0,
        "yes_no_questions": cleaned_yes_no_questions,
        "non_yes_no_questions": cleaned_non_yes_no_questions,
        "errors": cleaned_errors,
    }


def _find_question_span(raw_input: str, question_text: str) -> tuple[int, int] | None:
    """
    Finds the detected question inside the input.

    First tries exact case-insensitive matching.
    Then tries word-based matching to tolerate punctuation differences.
    """
    question_text = question_text.strip()

    if not question_text:
        return None

    exact_match = re.search(re.escape(question_text), raw_input, flags=re.IGNORECASE)

    if exact_match:
        return exact_match.start(), exact_match.end()

    question_words = re.findall(r"[A-Za-z]+", question_text.lower())

    if not question_words:
        return None

    input_tokens = list(re.finditer(r"[A-Za-z]+", raw_input))
    input_words = [token.group(0).lower() for token in input_tokens]

    for i in range(0, len(input_words) - len(question_words) + 1):
        if input_words[i : i + len(question_words)] == question_words:
            start = input_tokens[i].start()
            end = input_tokens[i + len(question_words) - 1].end()
            return start, end

    return None


def _remove_question_span(raw_input: str, question_text: str) -> str:
    span = _find_question_span(raw_input, question_text)

    if span is None:
        return raw_input.strip()

    start, end = span

    before = raw_input[:start]
    after = raw_input[end:]

    remaining = before + " " + after

    # Remove orphan punctuation left behind after removing the question.
    remaining = re.sub(r"\s+[?.!,]+\s*", " ", remaining)

    # Normalize whitespace only.
    remaining = re.sub(r"\s+", " ", remaining).strip()

    return remaining


def _question_exists_in_input(raw_input: str, question_text: str) -> bool:
    return _find_question_span(raw_input, question_text) is not None


def detect_single_yes_no_question(raw_input: str) -> Dict[str, Any]:
    """
    Normalizer Component N2: Question Detection.

    Main task is done by the LLM using QUESTION_DETECTION_PROMPT.

    N2-specific errors only:
    - No yes/no question detected
    - More than one yes/no question detected
    - Non yes/no question detected
    """
    text = raw_input or ""

    try:
        raw_result = _call_question_detection_llm(text)
    except Exception:
        return _make_failure([ERROR_NO_YES_NO])

    result = _normalize_llm_result(raw_result)

    yes_no_questions = result["yes_no_questions"]
    non_yes_no_questions = result["non_yes_no_questions"]
    llm_errors = result["errors"]

    # Tiny safety check:
    # Remove any question text that does not actually appear in the input.
    valid_yes_no_questions = []

    for question in yes_no_questions:
        question_text = question["text"]

        if _question_exists_in_input(text, question_text):
            valid_yes_no_questions.append(question)

    valid_non_yes_no_questions = []

    for question in non_yes_no_questions:
        question_text = question["text"]

        if _question_exists_in_input(text, question_text):
            valid_non_yes_no_questions.append(question)

    errors = []

    # Trust LLM errors, but recompute basic consistency from cleaned outputs.
    for error in llm_errors:
        if error not in errors:
            errors.append(error)

    if len(valid_yes_no_questions) == 0 and ERROR_NO_YES_NO not in errors:
        errors.append(ERROR_NO_YES_NO)

    if len(valid_yes_no_questions) > 1 and ERROR_MORE_THAN_ONE_YES_NO not in errors:
        errors.append(ERROR_MORE_THAN_ONE_YES_NO)

    if len(valid_non_yes_no_questions) > 0 and ERROR_NON_YES_NO not in errors:
        errors.append(ERROR_NON_YES_NO)

    if errors:
        return _make_failure(errors)

    question = valid_yes_no_questions[0]["text"]
    candidate_premise_text = _remove_question_span(text, question)

    return _make_success(
        question=question,
        candidate_premise_text=candidate_premise_text,
    )