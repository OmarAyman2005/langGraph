from typing import Any, Dict, List
import string

ALLOWED_PUNCTUATION = set(".,?!;:\"()-")
ALLOWED_WHITESPACE = set(" \t\n\r")


def _unique_in_order(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def _make_failure(
    original_input: Any,
    errors: List[str],
    non_english_characters: List[str] | None = None,
    unsupported_characters: List[str] | None = None,
) -> Dict[str, Any]:
    non_english_characters = non_english_characters or []
    unsupported_characters = unsupported_characters or []

    cleaned_errors = [
        error for error in errors if isinstance(error, str) and error.strip()
    ]

    if not cleaned_errors:
        cleaned_errors = ["Case unification failed"]

    return {
        "success": False,
        "case_unified_input": None,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
        "debug": {
            "original_input": original_input,
            "case_unified_input": None,
            "non_english_characters": non_english_characters,
            "unsupported_characters": unsupported_characters,
        },
    }


def _make_success(original_input: str, case_unified_input: str) -> Dict[str, Any]:
    return {
        "success": True,
        "case_unified_input": case_unified_input,
        "errors": [],
        "error": None,
        "debug": {
            "original_input": original_input,
            "case_unified_input": case_unified_input,
            "non_english_characters": [],
            "unsupported_characters": [],
        },
    }


def _find_invalid_characters(raw_input: str) -> Dict[str, List[str]]:
    non_english_characters = []
    unsupported_characters = []

    for ch in raw_input:
        # Non-English / non-ASCII characters:
        # Arabic letters, accented letters, emojis, Greek letters, etc.
        if not ch.isascii():
            non_english_characters.append(ch)
            continue

        # English letters and digits are allowed.
        if ch in string.ascii_letters or ch in string.digits:
            continue

        # Normal whitespace is allowed.
        if ch in ALLOWED_WHITESPACE:
            continue

        # Selected English punctuation is allowed.
        if ch in ALLOWED_PUNCTUATION:
            continue

        # Any remaining ASCII symbol is unsupported.
        unsupported_characters.append(ch)

    return {
        "non_english_characters": _unique_in_order(non_english_characters),
        "unsupported_characters": _unique_in_order(unsupported_characters),
    }


def unify_case(raw_input: str) -> Dict[str, Any]:
    """
    Normalizer Component N1: Case Unification.

    Responsibilities:
    1. Reject empty input.
    2. Reject non-English/non-ASCII characters.
    3. Reject unsupported ASCII symbols.
    4. Convert valid input to lowercase.

    This component does not use an LLM.
    """

    if raw_input is None:
        return _make_failure(
            original_input=raw_input,
            errors=["Empty input"],
        )

    if not isinstance(raw_input, str):
        return _make_failure(
            original_input=raw_input,
            errors=["Input must be a string"],
        )

    if not raw_input.strip():
        return _make_failure(
            original_input=raw_input,
            errors=["Empty input"],
        )

    invalid = _find_invalid_characters(raw_input)

    non_english_characters = invalid["non_english_characters"]
    unsupported_characters = invalid["unsupported_characters"]

    errors = []

    if non_english_characters:
        errors.append(
            "Non-English character(s) found: " + ", ".join(non_english_characters)
        )

    if unsupported_characters:
        errors.append(
            "Unsupported character(s) found: " + ", ".join(unsupported_characters)
        )

    if errors:
        return _make_failure(
            original_input=raw_input,
            errors=errors,
            non_english_characters=non_english_characters,
            unsupported_characters=unsupported_characters,
        )

    case_unified_input = raw_input.lower()

    return _make_success(
        original_input=raw_input,
        case_unified_input=case_unified_input,
    )
