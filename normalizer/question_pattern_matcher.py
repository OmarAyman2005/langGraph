import re
from typing import Any, Dict, List

from normalizer.sentence_pattern_matcher import _is_valid_atom_or_negated_atom


ERROR_QUESTION_PATTERN_MATCH = (
    "Question target does not map into a supported atomic proposition"
)

BE_AUXILIARIES = {"is", "are", "am", "was", "were"}

DO_AUXILIARIES = {"do", "does", "did"}

MODAL_OR_HAVE_AUXILIARIES = {
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

PARTICLES = {
    "up",
    "on",
    "off",
    "down",
    "out",
    "in",
    "over",
    "away",
    "back",
}


def _make_failure(errors: List[str] | None = None) -> Dict[str, Any]:
    cleaned_errors = []

    for error in errors or []:
        if isinstance(error, str) and error.strip():
            clean_error = error.strip()
            if clean_error not in cleaned_errors:
                cleaned_errors.append(clean_error)

    if not cleaned_errors:
        cleaned_errors = [ERROR_QUESTION_PATTERN_MATCH]

    return {
        "success": False,
        "question_pattern_success": False,
        "question": None,
        "target_candidates": [],
        "primary_target": None,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(
    question: str,
    target_candidates: List[str],
) -> Dict[str, Any]:
    return {
        "success": True,
        "question_pattern_success": True,
        "question": question,
        "target_candidates": target_candidates,
        "primary_target": target_candidates[0],
        "errors": [],
        "error": None,
    }


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _ensure_period(text: str) -> str:
    return _clean_text(text).rstrip(".").strip() + "."


def _strip_question_mark(question: str) -> str:
    return _clean_text(question).rstrip("?").strip()


def _verb_to_third_person(verb: str) -> str:
    lower = verb.lower()

    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return verb[:-1] + "ies"

    if lower.endswith(("s", "x", "z", "ch", "sh", "o")):
        return verb + "es"

    return verb + "s"


def _split_subject_and_verb_phrase(rest_words: List[str]) -> tuple[str, List[str]] | None:
    """
    Splits words after an auxiliary into:
    - subject
    - verb phrase

    Examples:
    ["ahmed", "study"] -> ("ahmed", ["study"])
    ["the", "guard", "wake", "up"] -> ("the guard", ["wake", "up"])
    ["the", "machine", "start"] -> ("the machine", ["start"])
    """

    if len(rest_words) < 2:
        return None

    if len(rest_words) >= 3 and rest_words[-1].lower() in PARTICLES:
        subject_words = rest_words[:-2]
        verb_phrase_words = rest_words[-2:]
    else:
        subject_words = rest_words[:-1]
        verb_phrase_words = rest_words[-1:]

    if not subject_words or not verb_phrase_words:
        return None

    return " ".join(subject_words), verb_phrase_words


def _convert_be_question(rest_words: List[str], aux: str) -> List[str]:
    """
    Converts be-auxiliary questions.

    Examples:
    is ahmed happy? -> ahmed is happy.
    is the ground wet? -> the ground is wet.
    is ahmed not happy? -> not ahmed is happy.
    """

    if len(rest_words) < 2:
        return []

    lowered_rest = [word.lower() for word in rest_words]

    # Negative be-question:
    # is ahmed not happy? -> not ahmed is happy.
    if "not" in lowered_rest:
        not_index = lowered_rest.index("not")

        subject_words = rest_words[:not_index]
        predicate_words = rest_words[not_index + 1:]

        if not subject_words or not predicate_words:
            return []

        subject = " ".join(subject_words)
        predicate = " ".join(predicate_words)

        return [_ensure_period(f"not {subject} {aux} {predicate}")]

    # Heuristic for be-question subject/predicate split:
    # is the ground wet? -> subject: the ground, predicate: wet
    # is ahmed a student? -> subject: ahmed, predicate: a student
    # is control screen on? -> subject: control screen, predicate: on
    if rest_words[0].lower() in {"the", "a", "an"} and len(rest_words) >= 3:
        subject = " ".join(rest_words[:2])
        predicate = " ".join(rest_words[2:])
    elif len(rest_words) >= 3 and rest_words[1].lower() in {"a", "an", "the"}:
        subject = rest_words[0]
        predicate = " ".join(rest_words[1:])
    else:
        subject = " ".join(rest_words[:-1])
        predicate = rest_words[-1]

    if not subject or not predicate:
        return []

    return [_ensure_period(f"{subject} {aux} {predicate}")]


def _convert_do_question(rest_words: List[str], aux: str) -> List[str]:
    """
    Converts do/does/did questions.

    For do/does, we return two target candidates:
    1. without do-support
    2. with explicit do-support

    This preserves your earlier design idea that do-questions may have two
    possible target atom forms.

    Examples:
    does ahmed study? -> ahmed studies. / ahmed does study.
    do they play? -> they play. / they do play.
    did ahmed study? -> ahmed did study.
    """

    split = _split_subject_and_verb_phrase(rest_words)
    if split is None:
        return []

    subject, verb_phrase_words = split

    if aux == "does":
        first_verb = _verb_to_third_person(verb_phrase_words[0])
        rest = verb_phrase_words[1:]

        without_do = " ".join([subject, first_verb] + rest)
        with_do = " ".join([subject, "does"] + verb_phrase_words)

        return [
            _ensure_period(without_do),
            _ensure_period(with_do),
        ]

    if aux == "do":
        without_do = " ".join([subject] + verb_phrase_words)
        with_do = " ".join([subject, "do"] + verb_phrase_words)

        return [
            _ensure_period(without_do),
            _ensure_period(with_do),
        ]

    if aux == "did":
        with_did = " ".join([subject, "did"] + verb_phrase_words)
        return [_ensure_period(with_did)]

    return []


def _convert_modal_or_have_question(rest_words: List[str], aux: str) -> List[str]:
    """
    Converts modal/have questions.

    Examples:
    can ahmed swim? -> ahmed can swim.
    has ahmed won? -> ahmed has won.
    will hla play well? -> hla will play well.
    """

    if len(rest_words) < 2:
        return []

    # Determiner-led subject:
    # will the machine start? -> the machine will start.
    # will the backup server respond? -> the backup server will respond.
    if rest_words[0].lower() in {"the", "a", "an"}:
        if len(rest_words) < 3:
            return []

        subject = " ".join(rest_words[:2])
        verb_phrase_words = rest_words[2:]
    else:
        # Single-token subject:
        # will hla play well? -> hla will play well.
        # can ahmed swim? -> ahmed can swim.
        subject = rest_words[0]
        verb_phrase_words = rest_words[1:]

    if not subject or not verb_phrase_words:
        return []

    target = " ".join([subject, aux] + verb_phrase_words)
    return [_ensure_period(target)]


def question_to_target_candidates(question: str) -> List[str]:
    """
    Converts a yes/no question into declarative target proposition candidate(s).

    Examples:
    is ahmed happy?
    -> ahmed is happy.

    does ahmed pass?
    -> ahmed passes.
    -> ahmed does pass.

    do they play?
    -> they play.
    -> they do play.

    did ahmed win?
    -> ahmed did win.

    will hla play well?
    -> hla will play well.
    """

    if not isinstance(question, str) or not question.strip():
        return []

    q = _strip_question_mark(question)
    words = q.split()

    if len(words) < 3:
        return []

    aux = words[0].lower()
    rest_words = words[1:]

    if aux in BE_AUXILIARIES:
        return _convert_be_question(rest_words, aux)

    if aux in DO_AUXILIARIES:
        return _convert_do_question(rest_words, aux)

    if aux in MODAL_OR_HAVE_AUXILIARIES:
        return _convert_modal_or_have_question(rest_words, aux)

    return []

def validate_question_pattern(question: str) -> Dict[str, Any]:
    """
    Normalizer Component N5: Question Pattern Matcher / Target Validator.

    Responsibilities:
    1. Convert the yes/no question into declarative target candidate(s).
    2. Validate that each candidate is a supported atomic target:
       - Fact X
       - Not X
    3. Reject unsupported targets such as:
       - quantifiers
       - comparisons
       - uncertainty
       - conjunctions/disjunctions/conditionals
    """

    if not isinstance(question, str) or not question.strip():
        return _make_failure([ERROR_QUESTION_PATTERN_MATCH])

    target_candidates = question_to_target_candidates(question)

    if not target_candidates:
        return _make_failure([ERROR_QUESTION_PATTERN_MATCH])

    valid_candidates = []

    for candidate in target_candidates:
        if _is_valid_atom_or_negated_atom(candidate):
            valid_candidates.append(candidate)

    if not valid_candidates:
        return _make_failure([ERROR_QUESTION_PATTERN_MATCH])

    return _make_success(
        question=question,
        target_candidates=valid_candidates,
    )