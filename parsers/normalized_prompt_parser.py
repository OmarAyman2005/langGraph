from typing import Any, Dict, List
import re

from normalizer.sentence_pattern_matcher import (
    normalize_single_sentence_pattern,
    _is_valid_atom_or_negated_atom,
)
from normalizer.question_pattern_matcher import question_to_target_candidates


ERROR_EMPTY_NORMALIZED_PROMPT = "Empty normalized prompt."
ERROR_MISSING_PREMISES_SECTION = "Missing Premises section."
ERROR_DUPLICATE_PREMISES_SECTION = "Duplicate Premises section."
ERROR_PREMISES_AFTER_QUESTION = "Premises section appears after Question section."
ERROR_MISSING_QUESTION_SECTION = "Missing Question section."
ERROR_DUPLICATE_QUESTION_SECTION = "Duplicate Question section."
ERROR_QUESTION_BEFORE_PREMISES = "Question section appears before Premises section."
ERROR_NO_PREMISES = "No premises found."
ERROR_MISSING_QUESTION_CONTENT = "Missing question content."
ERROR_MULTIPLE_QUESTION_LINES = "Multiple question lines found."
ERROR_UNEXPECTED_CONTENT = "Unexpected content before sections"
ERROR_MALFORMED_PREMISE_LINE = "Malformed premise line"
ERROR_INVALID_PREMISE_NUMBERING = "Invalid premise numbering"
ERROR_EMPTY_PREMISE_CONTENT = "Empty premise content"
ERROR_UNSUPPORTED_PREMISE = "Premise is not in a normalized recoverable form"
ERROR_UNSUPPORTED_QUESTION = "Question is not in a normalized recoverable form"


def _make_failure(error: str) -> Dict[str, Any]:
    return {
        "prompt_parse_success": False,
        "prompt_parse_error": error,
        "problem": None,
    }


def _make_success(premises: Dict[str, str], question: str) -> Dict[str, Any]:
    return {
        "prompt_parse_success": True,
        "prompt_parse_error": None,
        "problem": {
            "premises": premises,
            "question": question,
        },
    }


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _parse_premise_line(line: str) -> tuple[int, str] | None:
    """
    Parses one premise line.

    Expected:
    1. some premise.
    2. another premise.

    Returns:
    (number, content)
    """

    match = re.match(r"^(\d+)\.\s+(.+)$", line.strip())

    if not match:
        return None

    number = int(match.group(1))
    content = match.group(2).strip()

    return number, content


def _is_recoverable_normalized_premise(premise: str) -> bool:
    """
    Parser-level validation.

    The Normalizer should already have produced a supported sentence pattern.
    The parser only confirms that the sentence is still recoverable by the
    supported domain pattern matcher.
    """

    if not isinstance(premise, str) or not premise.strip():
        return False

    normalized = normalize_single_sentence_pattern(premise)

    return normalized is not None


def _is_recoverable_normalized_question(question: str) -> bool:
    """
    Parser-level validation.

    The question must be convertible into one or more supported atomic target
    proposition candidates.
    """

    if not isinstance(question, str) or not question.strip():
        return False

    target_candidates = question_to_target_candidates(question)

    if not target_candidates:
        return False

    for candidate in target_candidates:
        if not _is_valid_atom_or_negated_atom(candidate):
            return False

    return True


def parse_normalized_prompt(normalized_text: str) -> Dict[str, Any]:
    """
    Parser 1: Normalized User Prompt Parser.

    Input example:
    Premises:
    1. if it rains, then the ground is wet.
    2. it rains.

    Question:
    is the ground wet?

    Responsibilities:
    1. Read the Premises section.
    2. Extract each premise in order.
    3. Validate premise numbering: 1, 2, 3, ...
    4. Assign premise IDs: P1, P2, P3, ...
    5. Read exactly one Question section.
    6. Store the question as a separate field.
    7. Validate that each premise and question is still in a normalized,
       recoverable domain form.

    Output success:
    {
        "prompt_parse_success": True,
        "prompt_parse_error": None,
        "problem": {
            "premises": {
                "P1": "...",
                "P2": "..."
            },
            "question": "..."
        }
    }

    Output failure:
    {
        "prompt_parse_success": False,
        "prompt_parse_error": "...",
        "problem": None
    }
    """

    if not isinstance(normalized_text, str) or not normalized_text.strip():
        return _make_failure(ERROR_EMPTY_NORMALIZED_PROMPT)

    lines = [line.rstrip() for line in normalized_text.splitlines()]

    premises_started = False
    question_started = False

    premise_contents: List[str] = []
    question: str | None = None

    expected_premise_number = 1

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        # -------------------------------
        # Premises section header
        # -------------------------------
        if line == "Premises:":
            if question_started:
                return _make_failure(ERROR_PREMISES_AFTER_QUESTION)

            if premises_started:
                return _make_failure(ERROR_DUPLICATE_PREMISES_SECTION)

            premises_started = True
            continue

        # -------------------------------
        # Question section header
        # -------------------------------
        if line == "Question:":
            if not premises_started:
                return _make_failure(ERROR_QUESTION_BEFORE_PREMISES)

            if question_started:
                return _make_failure(ERROR_DUPLICATE_QUESTION_SECTION)

            question_started = True
            continue

        # -------------------------------
        # Question content
        # -------------------------------
        if question_started:
            if question is not None:
                return _make_failure(ERROR_MULTIPLE_QUESTION_LINES)

            question = _clean_line(line)
            continue

        # -------------------------------
        # Premise content
        # -------------------------------
        if premises_started:
            parsed = _parse_premise_line(line)

            if parsed is None:
                return _make_failure(f"{ERROR_MALFORMED_PREMISE_LINE}: '{line}'")

            number, content = parsed

            if number != expected_premise_number:
                return _make_failure(
                    f"{ERROR_INVALID_PREMISE_NUMBERING}: expected "
                    f"{expected_premise_number}, got {number} in line '{line}'"
                )

            if not content:
                return _make_failure(f"{ERROR_EMPTY_PREMISE_CONTENT}: '{line}'")

            content = _clean_line(content)

            if not _is_recoverable_normalized_premise(content):
                return _make_failure(f"{ERROR_UNSUPPORTED_PREMISE}: '{content}'")

            premise_contents.append(content)
            expected_premise_number += 1
            continue

        # -------------------------------
        # Content before any valid section
        # -------------------------------
        return _make_failure(f"{ERROR_UNEXPECTED_CONTENT}: '{line}'")

    # ==================================================
    # Final schema checks
    # ==================================================
    if not premises_started:
        return _make_failure(ERROR_MISSING_PREMISES_SECTION)

    if not premise_contents:
        return _make_failure(ERROR_NO_PREMISES)

    if not question_started:
        return _make_failure(ERROR_MISSING_QUESTION_SECTION)

    if question is None or not question.strip():
        return _make_failure(ERROR_MISSING_QUESTION_CONTENT)

    question = _clean_line(question)

    if not _is_recoverable_normalized_question(question):
        return _make_failure(f"{ERROR_UNSUPPORTED_QUESTION}: '{question}'")

    premises = {
        f"P{i + 1}": premise
        for i, premise in enumerate(premise_contents)
    }

    return _make_success(
        premises=premises,
        question=question,
    )