import re
from typing import Any, Dict, List


ERROR_NO_YES_NO = "No yes/no question detected"
ERROR_MORE_THAN_ONE_YES_NO = "More than one yes/no question detected"
ERROR_NON_YES_NO = "Non yes/no question detected"

AUXILIARIES = {
    "is",
    "are",
    "am",
    "was",
    "were",
    "do",
    "does",
    "did",
    "has",
    "have",
    "had",
    "will",
    "would",
    "can",
    "could",
    "shall",
    "should",
    "may",
    "might",
    "must",
}

BE_AUXILIARIES = {"is", "are", "am", "was", "were"}

WH_WORDS = {
    "what",
    "who",
    "whom",
    "whose",
    "where",
    "when",
    "why",
    "how",
    "which",
}

SENTENCE_BOUNDARIES = {".", "!", "?", "\n", "\r"}


def _unique_in_order(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def _make_failure(errors: List[str]) -> Dict[str, Any]:
    allowed = {
        ERROR_NO_YES_NO,
        ERROR_MORE_THAN_ONE_YES_NO,
        ERROR_NON_YES_NO,
    }

    cleaned_errors = []

    for error in errors:
        if isinstance(error, str) and error.strip() in allowed:
            clean = error.strip()
            if clean not in cleaned_errors:
                cleaned_errors.append(clean)

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


def _tokenize(text: str) -> List[str]:
    return [match.group(0).lower() for match in re.finditer(r"[A-Za-z0-9']+", text)]


def _starts_with_wh_question(text: str) -> bool:
    tokens = _tokenize(text)
    return bool(tokens) and tokens[0] in WH_WORDS


def _is_yes_no_question(question_text: str) -> bool:
    q = question_text.strip().rstrip("?").strip()
    tokens = _tokenize(q)

    if len(tokens) < 3:
        return False

    first = tokens[0]

    if first not in AUXILIARIES:
        return False

    if any(token in WH_WORDS for token in tokens):
        return False

    subject = tokens[1]
    predicate = tokens[2:]

    if not subject or not predicate:
        return False

    if first in BE_AUXILIARIES:
        if any(token in BE_AUXILIARIES for token in predicate):
            return False

    return True


def _classify_question_candidate(question_text: str) -> str:
    """
    Returns:
    - "yes_no"
    - "non_yes_no"
    """
    q = question_text.strip()

    if _is_yes_no_question(q):
        return "yes_no"

    return "non_yes_no"


def _find_question_start_for_chunk(chunk_before_qmark: str) -> int:
    """
    Given text before one '?', find where the actual question starts inside that chunk.

    Since inputs are well-punctuated, the question starts after the last sentence boundary
    before the question mark.
    """
    start = 0

    for i in range(len(chunk_before_qmark) - 1, -1, -1):
        if chunk_before_qmark[i] in SENTENCE_BOUNDARIES:
            start = i + 1
            break

    return start


def _extract_question_candidates(text: str) -> List[Dict[str, Any]]:
    """
    Extracts every candidate question ending with '?'.

    Each candidate includes the '?' exactly as it appears.
    """
    candidates = []

    for match in re.finditer(r"\?", text):
        qmark_index = match.start()
        chunk_before_qmark = text[:qmark_index]

        start = _find_question_start_for_chunk(chunk_before_qmark)
        end = qmark_index + 1

        question_text = text[start:end].strip()

        candidates.append(
            {
                "text": question_text,
                "start": start,
                "end": end,
            }
        )

    return candidates


def _remove_question_span(text: str, start: int, end: int) -> str:
    before = text[:start]
    after = text[end:]

    remaining = before + " " + after

    # Keep punctuation as much as possible, only clean whitespace introduced by removal.
    remaining = re.sub(r"\s+([.,!;:])", r"\1", remaining)
    remaining = re.sub(r"\s+", " ", remaining).strip()

    return remaining


def detect_single_yes_no_question(raw_input: str) -> Dict[str, Any]:
    """
    Normalizer Component N2: deterministic question detector.

    Rules:
    1. If there is no '?', fail with "No yes/no question detected".
    2. Extract all question candidates ending with '?'.
    3. Classify each candidate as:
       - proper yes/no question
       - non yes/no / malformed question
    4. If zero proper yes/no questions exist:
       "No yes/no question detected"
    5. If more than one proper yes/no question exists:
       "More than one yes/no question detected"
    6. If any non yes/no / malformed question exists:
       "Non yes/no question detected"
    7. Success only if exactly one proper yes/no question exists and no non yes/no
       question exists.
    """

    text = raw_input or ""

    if "?" not in text:
        return _make_failure([ERROR_NO_YES_NO])

    candidates = _extract_question_candidates(text)

    yes_no_questions = []
    non_yes_no_questions = []

    for candidate in candidates:
        question_text = candidate["text"].strip()

        if not question_text:
            non_yes_no_questions.append(candidate)
            continue

        label = _classify_question_candidate(question_text)

        if label == "yes_no":
            yes_no_questions.append(candidate)
        else:
            non_yes_no_questions.append(candidate)

    errors = []

    if len(yes_no_questions) == 0:
        errors.append(ERROR_NO_YES_NO)

    if len(yes_no_questions) > 1:
        errors.append(ERROR_MORE_THAN_ONE_YES_NO)

    if len(non_yes_no_questions) > 0:
        errors.append(ERROR_NON_YES_NO)

    if errors:
        return _make_failure(_unique_in_order(errors))

    question = yes_no_questions[0]

    candidate_premise_text = _remove_question_span(
        text=text,
        start=question["start"],
        end=question["end"],
    )

    return _make_success(
        question=question["text"],
        candidate_premise_text=candidate_premise_text,
    )