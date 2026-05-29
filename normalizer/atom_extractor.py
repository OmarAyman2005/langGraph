import re
from typing import Any, Dict, List, Tuple


ERROR_ATOM_EXTRACTION = "Atoms could not be extracted from premises"


def _make_failure(errors: List[str] | None = None) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors or []:
        if isinstance(error, str) and error.strip():
            clean_error = error.strip()
            if clean_error not in cleaned_errors:
                cleaned_errors.append(clean_error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_ATOM_EXTRACTION]

    return {
        "success": False,
        "atom_extraction_success": False,
        "premises": [],
        "atoms": [],
        "atom_table": [],
        "atom_occurrences": [],
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(
    premises: List[str],
    atom_table: List[Dict[str, Any]],
    atom_occurrences: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "success": True,
        "atom_extraction_success": True,
        "premises": premises,
        "atoms": atom_table,
        "atom_table": atom_table,
        "atom_occurrences": atom_occurrences,
        "errors": [],
        "error": None,
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _strip_period(text: str) -> str:
    return _clean(text).rstrip(".").strip()


def _ensure_period(text: str) -> str:
    return _strip_period(text) + "."


def _normalize_atom_key(atom: str) -> str:
    return _strip_period(atom).lower()


def _split_conditional(sentence: str) -> Tuple[str, str] | None:
    s = _strip_period(sentence)

    match = re.match(r"^if\s+(.+?)\s*,\s*then\s+(.+)$", s, flags=re.IGNORECASE)

    if not match:
        return None

    return match.group(1).strip(), match.group(2).strip()


def _split_conjunction(sentence: str) -> Tuple[str, str] | None:
    s = _strip_period(sentence)

    parts = re.split(r"\s+and\s+", s, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) != 2:
        return None

    return parts[0].strip(), parts[1].strip()


def _split_disjunction(sentence: str) -> Tuple[str, str] | None:
    s = _strip_period(sentence)

    parts = re.split(r"\s+or\s+", s, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) != 2:
        return None

    return parts[0].strip(), parts[1].strip()


def _extract_atom_from_clause(clause: str) -> Dict[str, Any] | None:
    """
    Extracts one base atom from a clause.

    Examples:
    ahmed studies
    -> atom_text: ahmed studies., polarity: positive

    not ahmed studies
    -> atom_text: ahmed studies., polarity: negative

    Important:
    In propositional logic, "not X" contains the atom X.
    The negation is stored as polarity in the occurrence, not as a new atom.
    """

    if not isinstance(clause, str) or not clause.strip():
        return None

    s = _strip_period(clause)

    if not s:
        return None

    polarity = "positive"

    if s.lower().startswith("not "):
        polarity = "negative"
        s = s[4:].strip()

    if not s:
        return None

    return {
        "atom_text": _ensure_period(s),
        "polarity": polarity,
    }


def _extract_atoms_from_premise(
    premise: str,
    premise_index: int,
) -> List[Dict[str, Any]] | None:
    """
    Extracts atom occurrences from one normalized premise.

    Supported premise forms after N6:
    - X.
    - not X.
    - X and Y.
    - X or Y.
    - if X, then Y.
    """

    if not isinstance(premise, str) or not premise.strip():
        return None

    s = _ensure_period(premise)

    conditional = _split_conditional(s)
    if conditional is not None:
        left, right = conditional

        left_atom = _extract_atom_from_clause(left)
        right_atom = _extract_atom_from_clause(right)

        if left_atom is None or right_atom is None:
            return None

        return [
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "conditional_antecedent",
                **left_atom,
            },
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "conditional_consequent",
                **right_atom,
            },
        ]

    conjunction = _split_conjunction(s)
    if conjunction is not None:
        left, right = conjunction

        left_atom = _extract_atom_from_clause(left)
        right_atom = _extract_atom_from_clause(right)

        if left_atom is None or right_atom is None:
            return None

        return [
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "conjunction_left",
                **left_atom,
            },
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "conjunction_right",
                **right_atom,
            },
        ]

    disjunction = _split_disjunction(s)
    if disjunction is not None:
        left, right = disjunction

        left_atom = _extract_atom_from_clause(left)
        right_atom = _extract_atom_from_clause(right)

        if left_atom is None or right_atom is None:
            return None

        return [
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "disjunction_left",
                **left_atom,
            },
            {
                "premise_index": premise_index,
                "premise": s,
                "role": "disjunction_right",
                **right_atom,
            },
        ]

    atom = _extract_atom_from_clause(s)

    if atom is None:
        return None

    role = "negated_fact" if atom["polarity"] == "negative" else "fact"

    return [
        {
            "premise_index": premise_index,
            "premise": s,
            "role": role,
            **atom,
        }
    ]


def extract_atoms_from_premises(premises: List[str]) -> Dict[str, Any]:
    """
    Normalizer Component N7: Extracting Atoms From Premises.

    Responsibilities:
    1. Read all normalized premises after N6.
    2. Extract all base atomic propositions from each premise.
    3. Add every unique atom to the Atom Table.
    4. Record each occurrence with:
       - source premise
       - role
       - polarity
    """

    if not isinstance(premises, list) or not premises:
        return _make_failure([ERROR_ATOM_EXTRACTION])

    atom_table = []
    atom_occurrences = []
    atom_key_to_id = {}

    normalized_premises = [_ensure_period(premise) for premise in premises]

    for premise_index, premise in enumerate(normalized_premises, start=1):
        occurrences = _extract_atoms_from_premise(
            premise=premise,
            premise_index=premise_index,
        )

        if occurrences is None:
            return _make_failure([ERROR_ATOM_EXTRACTION])

        for occurrence in occurrences:
            atom_text = occurrence["atom_text"]
            atom_key = _normalize_atom_key(atom_text)

            if atom_key not in atom_key_to_id:
                atom_id = f"A{len(atom_table) + 1}"
                atom_key_to_id[atom_key] = atom_id

                atom_table.append(
                    {
                        "atom_id": atom_id,
                        "atom_text": atom_text,
                    }
                )

            occurrence_with_id = {
                "atom_id": atom_key_to_id[atom_key],
                **occurrence,
            }

            atom_occurrences.append(occurrence_with_id)

    return _make_success(
        premises=normalized_premises,
        atom_table=atom_table,
        atom_occurrences=atom_occurrences,
    )