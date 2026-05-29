import re
from typing import Any, Dict, List

from normalizer.question_pattern_matcher import question_to_target_candidates
from normalizer.sentence_pattern_matcher import _is_valid_atom_or_negated_atom


ERROR_TARGET_ATOM_EXTRACTION = "Target atom could not be extracted from question"


def _make_failure(errors: List[str] | None = None) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors or []:
        if isinstance(error, str) and error.strip():
            clean_error = error.strip()
            if clean_error not in cleaned_errors:
                cleaned_errors.append(clean_error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_TARGET_ATOM_EXTRACTION]

    return {
        "success": False,
        "target_atom_extraction_success": False,
        "question": None,
        "target_atoms": [],
        "atom_table": [],
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(
    question: str,
    target_atoms: List[Dict[str, Any]],
    atom_table: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "success": True,
        "target_atom_extraction_success": True,
        "question": question,
        "target_atoms": target_atoms,
        "atom_table": atom_table,
        "errors": [],
        "error": None,
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _strip_period(text: str) -> str:
    return _clean(text).rstrip(".").strip()


def _ensure_period(text: str) -> str:
    return _strip_period(text) + "."


def _normalize_atom_key(atom_text: str) -> str:
    return _strip_period(atom_text).lower()


def _next_atom_number(atom_table: List[Dict[str, Any]]) -> int:
    max_number = 0

    for atom in atom_table:
        atom_id = str(atom.get("atom_id", ""))

        if atom_id.startswith("A"):
            number_part = atom_id[1:]

            if number_part.isdigit():
                max_number = max(max_number, int(number_part))

    return max_number + 1


def _copy_atom_table(atom_table: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    copied = []

    for atom in atom_table or []:
        if not isinstance(atom, dict):
            continue

        atom_id = atom.get("atom_id")
        atom_text = atom.get("atom_text")

        if atom_id and atom_text:
            copied.append(
                {
                    "atom_id": str(atom_id),
                    "atom_text": _ensure_period(str(atom_text)),
                }
            )

    return copied


def _add_atom_to_table(
    atom_text: str,
    atom_table: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], str]:
    """
    Adds atom to atom table if missing.
    Returns updated table and the atom_id.
    """

    clean_atom = _ensure_period(atom_text)
    atom_key = _normalize_atom_key(clean_atom)

    for atom in atom_table:
        existing_key = _normalize_atom_key(atom["atom_text"])

        if existing_key == atom_key:
            return atom_table, atom["atom_id"]

    next_number = _next_atom_number(atom_table)
    atom_id = f"A{next_number}"

    atom_table.append(
        {
            "atom_id": atom_id,
            "atom_text": clean_atom,
        }
    )

    return atom_table, atom_id


def extract_target_atoms_from_question(
    question: str,
    existing_atom_table: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Normalizer Component N8: Extracting Target Atom(s) From Question.

    Responsibilities:
    1. Receive the final subject-propagated question from N6.
    2. Convert it into declarative target atom candidate(s).
    3. For do/does questions, keep the two target candidates:
       - without do-support
       - with do-support
    4. Validate target candidates as supported atomic propositions.
    5. Add target atom(s) to the atom table if missing.
    """

    if not isinstance(question, str) or not question.strip():
        return _make_failure([ERROR_TARGET_ATOM_EXTRACTION])

    target_candidates = question_to_target_candidates(question)

    if not target_candidates:
        return _make_failure([ERROR_TARGET_ATOM_EXTRACTION])

    valid_candidates = []

    for candidate in target_candidates:
        clean_candidate = _ensure_period(candidate)

        if _is_valid_atom_or_negated_atom(clean_candidate):
            valid_candidates.append(clean_candidate)

    if not valid_candidates:
        return _make_failure([ERROR_TARGET_ATOM_EXTRACTION])

    atom_table = _copy_atom_table(existing_atom_table)
    target_atoms = []

    for candidate in valid_candidates:
        atom_table, atom_id = _add_atom_to_table(candidate, atom_table)

        target_atoms.append(
            {
                "atom_id": atom_id,
                "atom_text": candidate,
            }
        )

    return _make_success(
        question=question,
        target_atoms=target_atoms,
        atom_table=atom_table,
    )