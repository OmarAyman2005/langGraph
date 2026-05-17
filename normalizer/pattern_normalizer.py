import re
from typing import Any, Dict, List, Optional

from prompts import PREMISE_NORMALIZATION_PROMPT
from normalizer.llm_utils import call_llm_json
from normalizer.subject_propagator import propagate_plural_subject_in_conditional


def normalize_premise_with_llm(sentence: str) -> Dict[str, Any]:
    user_prompt = f"""Premise sentence:
{sentence}
"""
    return call_llm_json(PREMISE_NORMALIZATION_PROMPT, user_prompt)


def deterministic_conditional_rewrite(sentence: str) -> Optional[str]:
    s = sentence.strip().rstrip(".")

    lowered = s.lower()

    if not lowered.startswith("if "):
        return None

    # Case: If X, then Y
    if ", then " in lowered:
        return s + "."

    # Case: If X, Y
    if "," in s:
        left, right = s.split(",", 1)
        left = left.strip()
        right = right.strip()

        if left.lower().startswith("if ") and right:
            condition = left[3:].strip()
            return f"If {condition}, then {right}."
        # Case: If X then Y  -> If X, then Y
    if " then " in lowered:
        parts = re.split(r"\s+then\s+", s, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2 and parts[0].lower().startswith("if ") and parts[1].strip():
            condition = parts[0][3:].strip()
            consequence = parts[1].strip()
            return f"If {condition}, then {consequence}."
    return None


def is_quantified_or_general_statement(sentence: str) -> bool:
    lowered = sentence.strip().lower()
    return lowered.startswith(("all ", "every ", "some ", "no ", "most "))


def is_simple_atomic_fact(sentence: str) -> bool:
    lowered = sentence.strip().lower().rstrip(".")

    if is_quantified_or_general_statement(sentence):
        return False

    if lowered.startswith("if "):
        return False

    if lowered.startswith("not "):
        return False

    if " and " in lowered:
        return False

    if " or " in lowered:
        return False

    unsupported_markers = [
        " than ",
        " compared to ",
        " more than ",
        " less than ",
        " greater than ",
        " smaller than ",
        " larger than ",
        " before ",
        " after ",
        " because ",
        " since ",
        " although ",
        " while ",
    ]

    if any(marker in lowered for marker in unsupported_markers):
        return False

    return True


def contains_ambiguous_pronoun(premises: List[str]) -> bool:
    joined = " ".join(premises)

    # Detect proper-name-like tokens
    names = re.findall(r"\b[A-Z][a-z]+\b", joined)

    # Remove common sentence-start words that are not names
    non_names = {
        "If",
        "Then",
        "Not",
        "Either",
        "The",
        "A",
        "An",
        "It",
        "He",
        "She",
        "They",
    }

    possible_names = [name for name in names if name not in non_names]
    unique_names = set(possible_names)

    has_pronoun = bool(
        re.search(r"\b(he|she|they|him|her|them)\b", joined, re.IGNORECASE)
    )

    return has_pronoun and len(unique_names) > 1


def canonicalize_negation_sentence(sentence: str) -> Optional[str]:
    s = sentence.strip().rstrip(".")
    lowered = s.lower()

    # Already canonical
    if lowered.startswith("not "):
        return s + "."

    # X is not Y -> Not X is Y
    for marker in [" is not ", " are not ", " was not ", " were not "]:
        if marker in lowered:
            idx = lowered.index(marker)
            subject = s[:idx]
            aux = marker.strip().split()[0]
            rest = s[idx + len(marker) :]
            return f"Not {subject} {aux} {rest}."

    return None


def has_compound_subject(sentence: str) -> bool:
    lowered = sentence.strip().lower().rstrip(".")

    # Pattern: Name and Name are/is/was/were ...
    return bool(
        re.match(
            r"^[A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s+(is|are|was|were|has|have|will|can)\b",
            sentence.strip(),
        )
    )


def is_irrelevant_or_noisy_text(sentence: str) -> bool:
    lowered = sentence.strip().lower().rstrip(".")

    noise_starts = (
        "hello",
        "hi",
        "hey",
        "please",
        "can you",
        "could you",
        "solve this",
        "i think",
        "i believe",
        "this is easy",
        "this is hard",
        "let's",
        "lets",
    )

    if lowered.startswith(noise_starts):
        return True

    noise_phrases = (
        "please solve",
        "solve this",
        "i think",
        "i believe",
        "this is easy",
        "this is hard",
    )

    return any(phrase in lowered for phrase in noise_phrases)


def normalize_sentence_patterns(raw_premises: List[str]) -> Dict[str, Any]:
    normalized_premises = []

    if contains_ambiguous_pronoun(raw_premises):
        return {
            "success": False,
            "premises": [],
            "error": "Ambiguous pronoun reference",
        }

    for premise in raw_premises:
        if is_irrelevant_or_noisy_text(premise):
            return {
                "success": False,
                "premises": [],
                "error": "Irrelevant or noisy text",
            }

        if is_quantified_or_general_statement(premise):
            return {
                "success": False,
                "premises": [],
                "error": "Quantified/general/category-wide statement",
            }

        if has_compound_subject(premise):
            return {
                "success": False,
                "premises": [],
                "error": "Unsupported statement pattern",
            }

        deterministic_conditional = deterministic_conditional_rewrite(premise)

        if deterministic_conditional is not None:
            deterministic_conditional = propagate_plural_subject_in_conditional(
                deterministic_conditional
            )

            if (
                " then " in deterministic_conditional.lower()
                and not deterministic_conditional.lower().startswith("if ")
            ):
                return {
                    "success": False,
                    "premises": [],
                    "error": "Malformed conditional statement",
                }

            normalized_premises.append(deterministic_conditional)
            continue

        deterministic_negation = canonicalize_negation_sentence(premise)

        if deterministic_negation is not None:
            normalized_premises.append(deterministic_negation)
            continue

        if is_simple_atomic_fact(premise):
            normalized_premises.append(premise.strip().rstrip(".") + ".")
            continue

        normalized = normalize_premise_with_llm(premise)

        if not normalized.get("success"):
            return {
                "success": False,
                "premises": [],
                "error": normalized.get("error", "Unsupported statement pattern"),
            }

        normalized_sentence = (
            normalized["normalized_sentence"].strip().rstrip(".") + "."
        )

        rewritten_after_llm = deterministic_conditional_rewrite(normalized_sentence)

        if rewritten_after_llm is not None:
            normalized_sentence = rewritten_after_llm

        normalized_sentence = propagate_plural_subject_in_conditional(
            normalized_sentence
        )

        if (
            " then " in normalized_sentence.lower()
            and not normalized_sentence.lower().startswith("if ")
        ):
            return {
                "success": False,
                "premises": [],
                "error": "Malformed conditional statement",
            }

        normalized_premises.append(normalized_sentence)

    return {
        "success": True,
        "premises": normalized_premises,
        "error": None,
    }
