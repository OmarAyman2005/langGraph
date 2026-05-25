import re
from typing import Any, Dict, List


ERROR_PATTERN_MATCH = "One or more premises do not map into supported sentence patterns"


QUANTIFIERS = {
    "all",
    "some",
    "every",
    "each",
    "any",
    "most",
    "many",
    "few",
    "several",
}

UNCERTAINTY_WORDS = {
    "probably",
    "maybe",
    "possibly",
    "likely",
    "unlikely",
    "might",
}

UNSUPPORTED_RELATION_PHRASES = {
    "taller than",
    "shorter than",
    "larger than",
    "smaller than",
    "bigger than",
    "better than",
    "worse than",
    "more than",
    "less than",
}

RISKY_CONNECTIVE_WORDS = {
    "because",
    "since",
    "therefore",
    "hence",
    "so",
    "although",
    "unless",
    "while",
    "before",
    "after",
    "when",
    "whenever",
}

BE_FORMS = {
    "is",
    "are",
    "am",
    "was",
    "were",
}

MODAL_NEGATION_MAP = {
    "will not": "will",
    "cannot": "can",
    "can not": "can",
    "could not": "could",
    "should not": "should",
    "would not": "would",
    "must not": "must",
}


def _make_failure(
    errors: List[str] | None = None,
    failed_premises: List[str] | None = None,
) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors or []:
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
        "premises": [],
        "failed_premises": cleaned_failed_premises,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(pattern_matched_premises: List[str]) -> Dict[str, Any]:
    return {
        "success": True,
        "pattern_matched_premises": pattern_matched_premises,
        "premises": pattern_matched_premises,
        "failed_premises": [],
        "errors": [],
        "error": None,
    }


def _clean_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.strip())


def _strip_final_period(sentence: str) -> str:
    return sentence.strip().rstrip(".").strip()


def _ensure_period(sentence: str) -> str:
    sentence = _clean_sentence(sentence).rstrip(".").strip()
    return f"{sentence}."


def _word_tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text.lower()) is not None


def _has_any_word(text: str, words: set[str]) -> bool:
    return any(_contains_word(text, word) for word in words)


def _has_any_phrase(text: str, phrases: set[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _verb_to_third_person(verb: str) -> str:
    lower = verb.lower()

    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return verb[:-1] + "ies"

    if lower.endswith(("s", "x", "z", "ch", "sh", "o")):
        return verb + "es"

    return verb + "s"


def _is_complete_atomic_fact(text: str) -> bool:
    """
    Controlled approximation of Fact X.

    Fact X must be one atomic declarative proposition:
    - at least subject + predicate
    - no logical connectives
    - no quantifiers
    - no uncertainty
    - no comparisons/relations
    - no risky English connectives
    """

    s = _strip_final_period(text).lower()

    if not s:
        return False

    tokens = _word_tokens(s)

    if len(tokens) < 2:
        return False

    if _has_any_word(s, QUANTIFIERS):
        return False

    if _has_any_word(s, UNCERTAINTY_WORDS):
        return False

    if _has_any_phrase(s, UNSUPPORTED_RELATION_PHRASES):
        return False

    if _has_any_word(s, RISKY_CONNECTIVE_WORDS):
        return False

    # These are logical pattern words and should be handled by the pattern-level
    # matchers, not by Fact X.
    if _contains_word(s, "if"):
        return False

    if _contains_word(s, "or"):
        return False

    if _contains_word(s, "and"):
        return False

    return True


def _is_valid_atom_or_negated_atom(text: str) -> bool:
    s = _strip_final_period(text).strip()

    if s.lower().startswith("not "):
        inner = s[4:].strip()
        return _is_complete_atomic_fact(inner)

    return _is_complete_atomic_fact(s)


def _split_once_case_insensitive(text: str, pattern: str) -> List[str] | None:
    parts = re.split(pattern, text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    return [parts[0].strip(), parts[1].strip()]


# ==================================================
# Conditional matching / rewriting
# ==================================================

def _try_conditional(sentence: str) -> str | None:
    s = _strip_final_period(sentence)
    lowered = s.lower()

    # if X, then Y / if X then Y
    if lowered.startswith("if "):
        body = s[3:].strip()

        parts = _split_once_case_insensitive(body, r"\s*,?\s*then\s+")
        if parts is not None:
            left, right = parts

            if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
                return _ensure_period(f"if {left}, then {right}")

            return None

        # if X, Y
        parts = _split_once_case_insensitive(body, r"\s*,\s*")
        if parts is not None:
            left, right = parts

            if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
                return _ensure_period(f"if {left}, then {right}")

            return None

    # Y only if X -> if Y, then X
    parts = _split_once_case_insensitive(s, r"\s+only\s+if\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"if {left}, then {right}")

        return None

    # Y if X -> if X, then Y
    parts = _split_once_case_insensitive(s, r"\s+if\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"if {right}, then {left}")

        return None

    # X implies Y -> if X, then Y
    parts = _split_once_case_insensitive(s, r"\s+implies\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"if {left}, then {right}")

        return None

    return None


# ==================================================
# Negation matching / rewriting
# ==================================================

def _try_explicit_falsehood(sentence: str) -> str | None:
    s = _strip_final_period(sentence)
    lowered = s.lower()

    prefixes = [
        "it is false that ",
        "it is not true that ",
        "it is untrue that ",
    ]

    for prefix in prefixes:
        if lowered.startswith(prefix):
            inner = s[len(prefix):].strip()

            if _is_valid_atom_or_negated_atom(inner):
                return _ensure_period(f"not {inner}")

            return None

    return None


def _try_be_negation(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    patterns = [
        (r"\s+is\s+not\s+", "is"),
        (r"\s+are\s+not\s+", "are"),
        (r"\s+am\s+not\s+", "am"),
        (r"\s+was\s+not\s+", "was"),
        (r"\s+were\s+not\s+", "were"),
    ]

    for pattern, positive_be in patterns:
        parts = _split_once_case_insensitive(s, pattern)
        if parts is None:
            continue

        subject, rest = parts

        positive = f"{subject} {positive_be} {rest}"

        if _is_complete_atomic_fact(positive):
            return _ensure_period(f"not {positive}")

        return None

    return None


def _try_do_negation(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    # X does not V... / X doesn't V...
    patterns = [
        (r"\s+does\s+not\s+", "does"),
        (r"\s+do\s+not\s+", "do"),
        (r"\s+did\s+not\s+", "did"),
    ]

    for pattern, aux in patterns:
        parts = _split_once_case_insensitive(s, pattern)
        if parts is None:
            continue

        subject, verb_phrase = parts

        verb_words = verb_phrase.split()
        if not subject or not verb_words:
            return None

        if aux == "does":
            first_verb = _verb_to_third_person(verb_words[0])
            positive = " ".join([subject, first_verb] + verb_words[1:])
        elif aux == "do":
            positive = " ".join([subject] + verb_words)
        else:
            # Preserve did inside the proposition for safe explicit rewriting.
            positive = " ".join([subject, "did"] + verb_words)

        if _is_complete_atomic_fact(positive):
            return _ensure_period(f"not {positive}")

        return None

    return None


def _try_modal_negation(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    for negative_form, positive_modal in MODAL_NEGATION_MAP.items():
        pattern = rf"\s+{re.escape(negative_form)}\s+"
        parts = _split_once_case_insensitive(s, pattern)

        if parts is None:
            continue

        subject, rest = parts

        if not subject or not rest:
            return None

        positive = f"{subject} {positive_modal} {rest}"

        if _is_complete_atomic_fact(positive):
            return _ensure_period(f"not {positive}")

        return None

    return None


def _try_negation(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    # Already supported: not X
    if s.lower().startswith("not "):
        inner = s[4:].strip()

        if _is_valid_atom_or_negated_atom(inner):
            return _ensure_period(f"not {inner}")

        return None

    for matcher in [
        _try_explicit_falsehood,
        _try_be_negation,
        _try_do_negation,
        _try_modal_negation,
    ]:
        result = matcher(s)
        if result is not None:
            return result

    return None


# ==================================================
# Conjunction matching / rewriting
# ==================================================

def _try_conjunction(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    # both X and Y -> X and Y
    if s.lower().startswith("both "):
        body = s[5:].strip()
        parts = _split_once_case_insensitive(body, r"\s+and\s+")

        if parts is not None:
            left, right = parts

            if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
                return _ensure_period(f"{left} and {right}")

            return None

    # X as well as Y -> X and Y
    parts = _split_once_case_insensitive(s, r"\s+as\s+well\s+as\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"{left} and {right}")

        return None

    # X and also Y -> X and Y
    parts = _split_once_case_insensitive(s, r"\s+and\s+also\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"{left} and {right}")

        return None

    # X, and Y / X and Y
    parts = _split_once_case_insensitive(s, r"\s*,?\s+and\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"{left} and {right}")

        return None

    return None


# ==================================================
# Disjunction matching / rewriting
# ==================================================

def _try_disjunction(sentence: str) -> str | None:
    s = _strip_final_period(sentence)

    # either X or Y -> X or Y
    if s.lower().startswith("either "):
        body = s[7:].strip()
        parts = _split_once_case_insensitive(body, r"\s+or\s+")

        if parts is not None:
            left, right = parts

            if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
                return _ensure_period(f"{left} or {right}")

            return None

    # X or else Y -> X or Y
    parts = _split_once_case_insensitive(s, r"\s+or\s+else\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"{left} or {right}")

        return None

    # X, or Y / X or Y
    parts = _split_once_case_insensitive(s, r"\s*,?\s+or\s+")
    if parts is not None:
        left, right = parts

        if _is_valid_atom_or_negated_atom(left) and _is_valid_atom_or_negated_atom(right):
            return _ensure_period(f"{left} or {right}")

        return None

    return None


# ==================================================
# Main sentence classifier
# ==================================================

def normalize_single_sentence_pattern(sentence: str) -> str | None:
    """
    Returns the normalized supported sentence pattern if successful.
    Returns None if the premise cannot be safely mapped.
    """

    if not isinstance(sentence, str) or not sentence.strip():
        return None

    s = _clean_sentence(sentence)

    # Order matters:
    # conditionals before disjunction/conjunction/fact because they may contain
    # complete atoms on both sides.
    for matcher in [
        _try_conditional,
        _try_negation,
        _try_conjunction,
        _try_disjunction,
    ]:
        result = matcher(s)
        if result is not None:
            return result

    # Fact X
    if _is_complete_atomic_fact(s):
        return _ensure_period(s)

    return None


def match_sentence_patterns(premises: List[str]) -> Dict[str, Any]:
    """
    Normalizer Component N4: Sentence Pattern Matcher.

    Deterministic v1 behavior:
    - If a premise already matches one of the supported patterns, keep/normalize it.
    - If it safely rewrites into one of the supported patterns, rewrite it.
    - Otherwise fail with the N4-specific error.
    """

    if not isinstance(premises, list) or not premises:
        return _make_failure([ERROR_PATTERN_MATCH])

    normalized_premises = []
    failed_premises = []

    for premise in premises:
        normalized = normalize_single_sentence_pattern(premise)

        if normalized is None:
            failed_premises.append(premise)
        else:
            normalized_premises.append(normalized)

    if failed_premises:
        return _make_failure(
            errors=[ERROR_PATTERN_MATCH],
            failed_premises=failed_premises,
        )

    return _make_success(normalized_premises)


def normalize_sentence_patterns(premises: List[str]) -> Dict[str, Any]:
    """
    Compatibility wrapper for normalizer.py.

    Returns "premises" as the normalized premise list, because normalize_raw_prompt()
    expects pattern_result["premises"].
    """

    return match_sentence_patterns(premises)