import re
from typing import Any, Dict, List, Tuple


ERROR_SUBJECT_PROPAGATION = "Ambiguous subject propagation detected"

PRONOUNS = {"he", "she", "it", "they"}

BE_FORMS = {"is", "are", "am", "was", "were"}

AUXILIARIES = {
    "is",
    "are",
    "am",
    "was",
    "were",
    "has",
    "have",
    "had",
    "can",
    "could",
    "will",
    "would",
    "shall",
    "should",
    "may",
    "might",
    "must",
    "do",
    "does",
    "did",
}

DETERMINERS = {"the", "a", "an"}

PARTICLES = {"up", "on", "off", "down", "out", "in", "over", "away", "back"}


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
        cleaned_errors = [ERROR_SUBJECT_PROPAGATION]

    cleaned_failed_premises = []

    for premise in failed_premises or []:
        if isinstance(premise, str) and premise.strip():
            clean_premise = premise.strip()
            if clean_premise not in cleaned_failed_premises:
                cleaned_failed_premises.append(clean_premise)

    return {
        "success": False,
        "subject_propagation_success": False,
        "premises": [],
        "subject_propagated_premises": [],
        "question": None,
        "subject_propagated_question": None,
        "propagated_subjects": [],
        "failed_premises": cleaned_failed_premises,
        "errors": cleaned_errors,
        "error": "\n".join(cleaned_errors),
    }


def _make_success(
    premises: List[str],
    question: str,
    propagated_subjects: List[str],
) -> Dict[str, Any]:
    return {
        "success": True,
        "subject_propagation_success": True,
        "premises": premises,
        "subject_propagated_premises": premises,
        "question": question,
        "subject_propagated_question": question,
        "propagated_subjects": propagated_subjects,
        "failed_premises": [],
        "errors": [],
        "error": None,
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _strip_period(text: str) -> str:
    return text.strip().rstrip(".").strip()


def _ensure_period(text: str) -> str:
    return _clean(text).rstrip(".").strip() + "."


def _strip_question_mark(text: str) -> str:
    return text.strip().rstrip("?").strip()


def _ensure_question_mark(text: str) -> str:
    return _clean(text).rstrip("?").strip() + "?"


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _unique_in_order(items: List[str]) -> List[str]:
    result = []
    seen = set()

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def _starts_with_pronoun(clause: str) -> bool:
    words = _tokens(clause)
    return bool(words) and words[0] in PRONOUNS


def _starts_with_auxiliary(clause: str) -> bool:
    words = _tokens(clause)
    return bool(words) and words[0] in AUXILIARIES


def _looks_like_missing_subject_clause(clause: str) -> bool:
    """
    Detects simple cases where the second side of a binary sentence is missing
    the subject.

    Examples:
    - will stay home
    - plays tennis
    - sleeps
    - wins

    This is conservative and only used after N4 has already accepted the
    sentence as a valid supported pattern.
    """

    words = _tokens(clause)

    if not words:
        return False

    first = words[0]

    if first in PRONOUNS:
        return False

    if first in DETERMINERS:
        return False

    if first in AUXILIARIES:
        return True

    # Verb-like third-person predicate:
    # plays tennis, sleeps, wins, studies, passes
    if first.endswith("s"):
        return True

    return False


def _replace_initial_pronoun(clause: str, subject: str) -> str:
    words = clause.strip().split()

    if not words:
        return clause

    if words[0].lower() not in PRONOUNS:
        return clause

    return " ".join([subject] + words[1:])


def _add_missing_subject(clause: str, subject: str) -> str:
    return _clean(f"{subject} {clause}")


def _extract_simple_subject(clause: str) -> str | None:
    """
    Extracts a clear subject from a simple atomic clause.

    Supported safe cases:
    - ahmed studies
    - sara sleeps
    - ahmed plays football
    - the sensor is active
    - the guard wakes up
    """

    words = _tokens(clause)

    if len(words) < 2:
        return None

    first = words[0]

    if first in PRONOUNS:
        return None

    if first in DETERMINERS:
        for i, word in enumerate(words):
            if i > 0 and word in AUXILIARIES:
                subject_words = words[:i]
                if len(subject_words) >= 2:
                    return " ".join(subject_words)
                return None

        if len(words) >= 3:
            return " ".join(words[:2])

        return None

    return first


def _count_possible_entities(clause: str) -> int:
    """
    Conservative local ambiguity detector.

    Safe:
    - ahmed studies
    - ahmed plays football
    - the sensor is active
    - the guards arrive
    - the door opens

    Ambiguous:
    - the sensor triggers the alarm
    - ahmed helps sara
    """

    words = _tokens(clause)

    if len(words) < 2:
        return 0

    if words[0] in DETERMINERS:
        count = 1

        for i in range(2, len(words) - 1):
            if words[i] in DETERMINERS:
                count += 1

        return count

    if words[0] in PRONOUNS:
        return 0

    count = 1

    # Conservative special case:
    # if there is a later capital-name-like object, after N1 we cannot know
    # capitalization, so we approximate only for known multi-entity patterns
    # through determiner phrases and through simple "name verb name" shape.
    if len(words) == 3:
        subject, verb, obj = words

        if subject not in DETERMINERS and obj not in PARTICLES:
            relational_verbs = {
                "helps",
                "help",
                "meets",
                "meet",
                "visits",
                "visit",
                "sees",
                "see",
                "calls",
                "call",
                "knows",
                "know",
            }

            if verb in relational_verbs:
                count += 1

    return count


def _source_is_ambiguous(clause: str) -> bool:
    return _count_possible_entities(clause) > 1


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


def _propagate_in_binary_pattern(
    left: str,
    right: str,
    rebuild_kind: str,
    original_sentence: str,
) -> tuple[str | None, str | None]:
    """
    Returns:
    - (rewritten_sentence, propagated_subject) if propagation applies
    - (original_sentence, None) if no propagation needed
    - (None, None) if propagation is needed but ambiguous/unsafe
    """

    needs_pronoun_propagation = _starts_with_pronoun(right)
    needs_missing_subject_propagation = _looks_like_missing_subject_clause(right)

    if not needs_pronoun_propagation and not needs_missing_subject_propagation:
        return original_sentence, None

    if _source_is_ambiguous(left):
        return None, None

    subject = _extract_simple_subject(left)

    if subject is None:
        return None, None

    if needs_pronoun_propagation:
        new_right = _replace_initial_pronoun(right, subject)
    else:
        new_right = _add_missing_subject(right, subject)

    if rebuild_kind == "conditional":
        return _ensure_period(f"if {left}, then {new_right}"), subject

    if rebuild_kind == "conjunction":
        return _ensure_period(f"{left} and {new_right}"), subject

    if rebuild_kind == "disjunction":
        return _ensure_period(f"{left} or {new_right}"), subject

    return original_sentence, None


def propagate_subject_in_premise(premise: str) -> tuple[str | None, str | None]:
    """
    Applies local subject propagation inside one normalized premise.

    Handles:
    - if X, then Pronoun ...
    - X and Pronoun ...
    - X or Pronoun ...
    - if X, then MissingSubjectPredicate
    - X and MissingSubjectPredicate
    - X or MissingSubjectPredicate
    """

    if not isinstance(premise, str) or not premise.strip():
        return None, None

    s = _ensure_period(premise)

    conditional = _split_conditional(s)
    if conditional is not None:
        left, right = conditional
        return _propagate_in_binary_pattern(
            left=left,
            right=right,
            rebuild_kind="conditional",
            original_sentence=s,
        )

    conjunction = _split_conjunction(s)
    if conjunction is not None:
        left, right = conjunction
        return _propagate_in_binary_pattern(
            left=left,
            right=right,
            rebuild_kind="conjunction",
            original_sentence=s,
        )

    disjunction = _split_disjunction(s)
    if disjunction is not None:
        left, right = disjunction
        return _propagate_in_binary_pattern(
            left=left,
            right=right,
            rebuild_kind="disjunction",
            original_sentence=s,
        )

    return s, None


def _premise_has_pronoun_subject(premise: str) -> bool:
    words = _tokens(premise)

    if not words:
        return False

    return words[0] in PRONOUNS


def _replace_premise_pronoun_subject(premise: str, subject: str) -> str:
    words = _strip_period(premise).split()

    if not words:
        return premise

    if words[0].lower() not in PRONOUNS:
        return _ensure_period(premise)

    return _ensure_period(" ".join([subject] + words[1:]))


def _question_has_pronoun_subject(question: str) -> bool:
    words = _tokens(_strip_question_mark(question))

    if len(words) < 3:
        return False

    return words[1] in PRONOUNS


def _replace_question_pronoun_subject(question: str, subject: str) -> str:
    q = _strip_question_mark(question)
    words = q.split()

    if len(words) < 3:
        return _ensure_question_mark(question)

    if words[1].lower() not in PRONOUNS:
        return _ensure_question_mark(question)

    return _ensure_question_mark(" ".join([words[0], subject] + words[2:]))


def _collect_concrete_subjects_from_premises(premises: List[str]) -> List[str]:
    subjects = []

    for premise in premises:
        if not isinstance(premise, str) or not premise.strip():
            continue

        s = _ensure_period(premise)

        conditional = _split_conditional(s)
        if conditional is not None:
            left, right = conditional

            left_subject = _extract_simple_subject(left)
            right_subject = _extract_simple_subject(right)

            if left_subject is not None:
                subjects.append(left_subject)

            if right_subject is not None:
                subjects.append(right_subject)

            continue

        conjunction = _split_conjunction(s)
        if conjunction is not None:
            left, right = conjunction

            left_subject = _extract_simple_subject(left)
            right_subject = _extract_simple_subject(right)

            if left_subject is not None:
                subjects.append(left_subject)

            if right_subject is not None:
                subjects.append(right_subject)

            continue

        disjunction = _split_disjunction(s)
        if disjunction is not None:
            left, right = disjunction

            left_subject = _extract_simple_subject(left)
            right_subject = _extract_simple_subject(right)

            if left_subject is not None:
                subjects.append(left_subject)

            if right_subject is not None:
                subjects.append(right_subject)

            continue

        subject = _extract_simple_subject(s)

        if subject is not None:
            subjects.append(subject)

    return _unique_in_order(subjects)


def _apply_global_single_subject_propagation(
    premises: List[str],
    question: str,
    concrete_subjects: List[str],
) -> tuple[List[str] | None, str | None]:
    """
    Applies cross-sentence pronoun propagation only if exactly one clear
    concrete subject exists in the whole prompt.
    """

    any_pronoun_needs_resolution = any(
        _premise_has_pronoun_subject(premise) for premise in premises
    ) or _question_has_pronoun_subject(question)

    if not any_pronoun_needs_resolution:
        return premises, question

    if len(concrete_subjects) != 1:
        return None, None

    subject = concrete_subjects[0]

    updated_premises = []

    for premise in premises:
        if _premise_has_pronoun_subject(premise):
            updated_premises.append(_replace_premise_pronoun_subject(premise, subject))
        else:
            updated_premises.append(_ensure_period(premise))

    updated_question = question

    if _question_has_pronoun_subject(question):
        updated_question = _replace_question_pronoun_subject(question, subject)

    return updated_premises, updated_question

def _pre_resolve_pronouns_with_global_subject(
    premise: str,
    global_subject: str | None,
) -> str:
    """
    If exactly one concrete subject exists globally, resolve pronoun subjects
    before local propagation, but only when doing so is safe.

    Critical safety rule:
    If the left/source side is ambiguous and the right side starts with a pronoun,
    do NOT pre-resolve it. Leave it unchanged so the normal local propagation
    step can reject it as ambiguous.

    Examples:
    Safe:
    mariam practices daily.
    if she practices daily, then she improves.
    -> if mariam practices daily, then mariam improves.

    Unsafe:
    ahmed helps sara and she studies.
    -> leave unchanged so N6 rejects it as ambiguous.

    Unsafe:
    if the sensor triggers the alarm, then it rings.
    -> leave unchanged so N6 rejects it as ambiguous.
    """

    if global_subject is None:
        return _ensure_period(premise)

    s = _ensure_period(premise)

    conditional = _split_conditional(s)
    if conditional is not None:
        left, right = conditional

        # Case: if pronoun..., then ...
        # Safe because the pronoun source itself can be replaced by the one
        # known global concrete subject.
        if _starts_with_pronoun(left):
            left = _replace_initial_pronoun(left, global_subject)

        # Case: if X, then pronoun...
        # Only safe if X is not ambiguous.
        if _starts_with_pronoun(right):
            if _source_is_ambiguous(left):
                return s
            right = _replace_initial_pronoun(right, global_subject)

        return _ensure_period(f"if {left}, then {right}")

    conjunction = _split_conjunction(s)
    if conjunction is not None:
        left, right = conjunction

        if _starts_with_pronoun(left):
            left = _replace_initial_pronoun(left, global_subject)

        if _starts_with_pronoun(right):
            if _source_is_ambiguous(left):
                return s
            right = _replace_initial_pronoun(right, global_subject)

        return _ensure_period(f"{left} and {right}")

    disjunction = _split_disjunction(s)
    if disjunction is not None:
        left, right = disjunction

        if _starts_with_pronoun(left):
            left = _replace_initial_pronoun(left, global_subject)

        if _starts_with_pronoun(right):
            if _source_is_ambiguous(left):
                return s
            right = _replace_initial_pronoun(right, global_subject)

        return _ensure_period(f"{left} or {right}")

    if _premise_has_pronoun_subject(s):
        return _replace_premise_pronoun_subject(s, global_subject)

    return s

def propagate_subjects(
    premises: List[str],
    question: str | None = None,
) -> Dict[str, Any]:
    """
    Normalizer Component N6: Subject Propagation.

    Deterministic behavior:
    1. Applies local subject propagation inside compound premise sentences.
    2. Adds missing subjects in the second side of conditionals/conjunctions/disjunctions.
    3. If exactly one concrete subject exists globally, pronoun-starting premises,
       pronoun-starting clauses, and pronoun-subject questions may be resolved to it.
    4. If zero concrete subjects exist, pronouns are treated as explicit subjects and
       left unchanged.
    5. If multiple concrete subjects exist and a pronoun needs resolution, reject as
       ambiguous.
    """

    if not isinstance(premises, list) or not premises:
        return _make_failure([ERROR_SUBJECT_PROPAGATION])

    active_question = question or ""

    # --------------------------------------------------
    # Step 1: collect concrete subjects before propagation
    # --------------------------------------------------
    initial_concrete_subjects = _collect_concrete_subjects_from_premises(premises)

    global_subject = None

    if len(initial_concrete_subjects) == 1:
        global_subject = initial_concrete_subjects[0]

    # --------------------------------------------------
    # Step 2: if exactly one global concrete subject exists,
    # pre-resolve pronoun subjects inside premises/clauses.
    # --------------------------------------------------
    preprocessed_premises = []

    for premise in premises:
        updated = _pre_resolve_pronouns_with_global_subject(
            premise=premise,
            global_subject=global_subject,
        )
        preprocessed_premises.append(updated)

    # --------------------------------------------------
    # Step 3: local propagation inside each premise
    # --------------------------------------------------
    locally_propagated_premises = []
    locally_propagated_subjects = []
    failed_premises = []

    for premise in preprocessed_premises:
        result, subject = propagate_subject_in_premise(premise)

        if result is None:
            failed_premises.append(premise)
        else:
            locally_propagated_premises.append(result)

        if subject is not None:
            locally_propagated_subjects.append(subject)

    if failed_premises:
        return _make_failure(
            errors=[ERROR_SUBJECT_PROPAGATION],
            failed_premises=failed_premises,
        )

    # --------------------------------------------------
    # Step 4: collect concrete subjects again after local propagation
    # --------------------------------------------------
    concrete_subjects = _collect_concrete_subjects_from_premises(
        locally_propagated_premises
    )

    # --------------------------------------------------
    # Step 5: question propagation
    # --------------------------------------------------
    final_question = active_question

    if _question_has_pronoun_subject(active_question):
        if len(concrete_subjects) == 0:
            # Pronoun-only prompt, e.g.:
            # he played. he won. did he win?
            # No concrete subject exists, so leave the pronoun unchanged.
            final_question = _ensure_question_mark(active_question)

        elif len(concrete_subjects) == 1:
            final_question = _replace_question_pronoun_subject(
                question=active_question,
                subject=concrete_subjects[0],
            )

        else:
            return _make_failure(
                errors=[ERROR_SUBJECT_PROPAGATION],
                failed_premises=[],
            )
    else:
        final_question = _ensure_question_mark(active_question)

    propagated_subjects = _unique_in_order(
        locally_propagated_subjects + concrete_subjects
    )

    return _make_success(
        premises=locally_propagated_premises,
        question=final_question,
        propagated_subjects=propagated_subjects,
    )