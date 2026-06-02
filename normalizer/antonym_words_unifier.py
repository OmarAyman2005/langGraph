"""
N8 — Antonym Words Unifier.

Purpose:
- Takes the normalized prompt after N7.
- Detects direct antonym words using NLTK WordNet only.
- Keeps the earlier occurring word.
- Rewrites later antonym atoms/questions as negations of the earlier word form.
- Performs no LLM calls.

Important behavior:
- Exact same words do not trigger antonym unification.
  Example: open / open -> no change.
- Opposite words do trigger antonym unification.
  Example: open / closed -> closed becomes not open.
- Already-negated antonym cases are handled through double-negation cleanup.
  Example:
      sara is good.
      is sara not bad?
  becomes:
      sara is good.
      is sara good?
- Rewritten premise sentences are passed through N4-style normalization so that:
      ahmed is not strong.
  becomes:
      not ahmed is strong.
- Double negation is cancelled when formed:
      not not ahmed is strong.
  becomes:
      ahmed is strong.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from normalizer.semantic_lexicon import (
    are_direct_antonyms,
    get_best_base_form,
    wordnet_is_available,
)
from normalizer.sentence_pattern_matcher import normalize_single_sentence_pattern


WORD_PATTERN = re.compile(r"\b[a-zA-Z]+\b")

SECTION_LABELS = {"premises", "question"}

FUNCTION_WORDS_TO_IGNORE = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "if",
    "then",
    "not",
    "is",
    "are",
    "am",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "for",
    "with",
    "from",
    "as",
    "that",
    "this",
    "these",
    "those",
    "he",
    "she",
    "it",
    "they",
    "we",
    "you",
    "i",
    "premises",
    "question",
}

BE_VERBS = {"is", "are", "am", "was", "were"}
DO_AUXILIARIES = {"do", "does", "did"}


# ==================================================
# Result helpers
# ==================================================

def make_failure(error: str) -> Dict[str, Any]:
    return {
        "success": False,
        "text": None,
        "changes": [],
        "error": error,
    }


def make_success(text: str, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "success": True,
        "text": text,
        "changes": changes,
        "error": None,
    }


# ==================================================
# Basic helpers
# ==================================================

def clean_word(word: str) -> str:
    return word.lower().strip()


def clean_spaces(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"\s+([.?])", r"\1", text)
    return text


def ensure_period(text: str) -> str:
    return clean_spaces(text).rstrip(".").strip() + "."


def ensure_question_mark(text: str) -> str:
    return clean_spaces(text).rstrip("?").strip() + "?"


def strip_final_period_or_question(text: str) -> str:
    return clean_spaces(text).rstrip(".?").strip()


def is_ignored_word(word: str) -> bool:
    return clean_word(word) in FUNCTION_WORDS_TO_IGNORE


def split_sentence_spans(text: str) -> List[Tuple[int, int, str]]:
    """
    Splits normalized prompt into actual premise/question sentence lines.

    This intentionally skips section labels:
    Premises:
    Question:

    So the question sentence is treated as:
    is the door closed?

    not:
    Question:
    is the door closed?
    """

    spans: List[Tuple[int, int, str]] = []

    offset = 0

    for line in text.splitlines(keepends=True):
        raw_line = line
        stripped_line = raw_line.strip()

        line_start = offset
        line_end = offset + len(raw_line)
        offset = line_end

        if not stripped_line:
            continue

        if stripped_line.lower() in {"premises:", "question:"}:
            continue

        leading_spaces = len(raw_line) - len(raw_line.lstrip())
        trailing_spaces = len(raw_line) - len(raw_line.rstrip())

        real_start = line_start + leading_spaces
        real_end = line_end - trailing_spaces

        sentence = text[real_start:real_end].strip()

        if sentence:
            spans.append((real_start, real_end, sentence))

    return spans


def last_content_word_index(words: List[str], start_index: int = 0) -> Optional[int]:
    for index in range(len(words) - 1, start_index - 1, -1):
        if words[index] not in FUNCTION_WORDS_TO_IGNORE:
            return index

    return None


def infer_word_role(sentence_words: List[str], word_index: int) -> str:
    """
    Infers a rough role for the word.

    Returns:
    - be_complement
    - do_question_predicate
    - simple_predicate
    - other
    """

    if word_index <= 0 or word_index >= len(sentence_words):
        return "other"

    previous_word = sentence_words[word_index - 1]

    if previous_word in BE_VERBS:
        return "be_complement"

    be_indexes = [i for i, word in enumerate(sentence_words) if word in BE_VERBS]

    if be_indexes:
        first_be_index = be_indexes[0]
        final_content_index = last_content_word_index(
            sentence_words,
            start_index=first_be_index + 1,
        )

        if final_content_index is not None and word_index == final_content_index:
            return "be_complement"

        return "other"

    do_indexes = [i for i, word in enumerate(sentence_words) if word in DO_AUXILIARIES]

    if do_indexes:
        first_do_index = do_indexes[0]
        final_content_index = last_content_word_index(
            sentence_words,
            start_index=first_do_index + 1,
        )

        if final_content_index is not None and word_index == final_content_index:
            return "do_question_predicate"

        return "other"

    # Simple statement: ahmed passes.
    if word_index == 1:
        return "simple_predicate"

    # Article subject form: the match starts.
    if (
        len(sentence_words) >= 3
        and sentence_words[0] in {"the", "a", "an"}
        and word_index == 2
    ):
        return "simple_predicate"

    return "other"


def strip_numbering_prefix(sentence: str) -> tuple[str, str]:
    """
    Example:
    2. the door is closed. -> ("2. ", "the door is closed.")
    """

    match = re.match(r"^(\d+\.\s+)(.+)$", sentence.strip())

    if not match:
        return "", sentence.strip()

    return match.group(1), match.group(2)


def sentence_is_question(sentence_body: str) -> bool:
    words = [clean_word(match.group(0)) for match in WORD_PATTERN.finditer(sentence_body)]

    if not words:
        return False

    return words[0] in BE_VERBS or words[0] in DO_AUXILIARIES


# ==================================================
# Morphology helpers
# ==================================================

def inflect_third_person_singular(base: str) -> str:
    base = clean_word(base)

    if not base:
        return base

    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ies"

    if base.endswith(("s", "sh", "ch", "x", "z", "o")):
        return base + "es"

    return base + "s"


def inflect_present_participle(base: str) -> str:
    base = clean_word(base)

    if not base:
        return base

    if base.endswith("ie"):
        return base[:-2] + "ying"

    if base.endswith("e") and not base.endswith("ee"):
        return base[:-1] + "ing"

    return base + "ing"


def adapt_earlier_word_for_later_context(
    earlier_word: str,
    later_word: str,
    later_role: str,
) -> str:
    earlier = clean_word(earlier_word)
    later = clean_word(later_word)

    if later_role == "be_complement":
        return earlier

    earlier_base = get_best_base_form(earlier)
    later_base = get_best_base_form(later)

    if later_role == "do_question_predicate":
        return earlier_base

    if later == later_base:
        return earlier_base

    if later.endswith("ing"):
        return inflect_present_participle(earlier_base)

    if later.endswith("s"):
        return inflect_third_person_singular(earlier_base)

    return earlier


# ==================================================
# Double-negation cleanup helpers
# ==================================================

def collapse_adjacent_double_not(text: str) -> str:
    """
    Removes directly adjacent double negation.

    Examples:
    not not ahmed is strong. -> ahmed is strong.
    is sara not not good? -> is sara good?
    """

    updated = text

    while re.search(r"\bnot\s+not\b", updated, flags=re.IGNORECASE):
        updated = re.sub(
            r"\bnot\s+not\s*",
            "",
            updated,
            count=1,
            flags=re.IGNORECASE,
        )
        updated = clean_spaces(updated)

    return updated


def simplify_statement_double_negation(sentence_body: str) -> str:
    """
    Simplifies double negation in statement bodies.

    Handles:
    - not not ahmed is strong. -> ahmed is strong.
    - not ahmed is not strong. -> ahmed is strong.

    The second case is handled by using N4's sentence-pattern normalization:
    inner: ahmed is not strong.
    N4(inner): not ahmed is strong.
    outer not + inner not cancel.
    """

    body = ensure_period(sentence_body)

    # Direct adjacent case: not not X.
    body = ensure_period(collapse_adjacent_double_not(body))

    lowered = body.lower().strip()

    # Outer negation case: not <inner>.
    if lowered.startswith("not "):
        inner = body.strip()[4:].strip()
        inner = ensure_period(inner)

        inner_normalized = normalize_single_sentence_pattern(inner)

        # If the inner statement itself normalizes to not X, then:
        # not (not X) => X
        if (
            isinstance(inner_normalized, str)
            and inner_normalized.lower().startswith("not ")
        ):
            positive = inner_normalized.strip()[4:].strip()
            positive = ensure_period(positive)
            positive = collapse_adjacent_double_not(positive)
            return ensure_period(positive)

    return body


def simplify_question_double_negation(question_body: str) -> str:
    """
    Simplifies double negation in question bodies.

    Example:
    is sara not not good? -> is sara good?
    """

    question = ensure_question_mark(question_body)
    question = collapse_adjacent_double_not(question)
    return ensure_question_mark(question)


def normalize_rewritten_premise_sentence(sentence: str) -> str:
    """
    Applies N4-style normalization only to premise sentences.

    This converts:
    ahmed is not strong. -> not ahmed is strong.

    Then applies double-negation cleanup:
    not not ahmed is strong. -> ahmed is strong.
    not ahmed is not strong. -> ahmed is strong.
    """

    prefix, body = strip_numbering_prefix(sentence.strip())

    body = ensure_period(body)

    # First cleanup possible double negation created by antonym unification.
    body = simplify_statement_double_negation(body)

    # Then call N4's pattern normalization on the affected premise body.
    normalized_body = normalize_single_sentence_pattern(body)

    if isinstance(normalized_body, str) and normalized_body.strip():
        body = normalized_body

    # Final cleanup in case N4 normalization exposed another double negation.
    body = simplify_statement_double_negation(body)

    return prefix + body


def normalize_rewritten_question_sentence(sentence: str) -> str:
    """
    Applies only double-negation cleanup to questions.

    Important:
    We do NOT call N4 on questions.
    The rest of the pipeline can handle questions like:
    is khaled not tall?
    """

    return simplify_question_double_negation(sentence.strip())


def postprocess_rewritten_text(text: str) -> str:
    """
    After antonym rewrites are applied, clean the normalized prompt.

    Rules:
    - Premise lines are passed through N4-style normalization.
    - Question line is only double-negation-cleaned.
    - Section labels and blank lines are preserved.
    """

    output_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            output_lines.append(raw_line)
            continue

        if stripped.lower() in {"premises:", "question:"}:
            output_lines.append(raw_line)
            continue

        leading_spaces = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        if stripped.endswith("?"):
            processed = normalize_rewritten_question_sentence(stripped)
        else:
            processed = normalize_rewritten_premise_sentence(stripped)

        output_lines.append(leading_spaces + processed)

    return "\n".join(output_lines)


# ==================================================
# Rewrite helpers
# ==================================================

def replace_word_span(
    sentence_body: str,
    word_start: int,
    word_end: int,
    replacement_word: str,
) -> str:
    return sentence_body[:word_start] + replacement_word + sentence_body[word_end:]


def add_antonym_negation_to_statement(
    sentence_body: str,
    replacement_word_start: int,
) -> str:
    """
    Adds the antonym-negation layer to a statement.

    For be-complement cases, this produces the natural intermediate form:
        ahmed is strong. -> ahmed is not strong.
        not ahmed is strong. -> not ahmed is not strong.

    This allows the debug output to show the exact intermediate stage before
    N4-style normalization.

    For non-be/simple predicate cases, it falls back to the safer canonical
    external negation:
        sara passes. -> not sara passes.
    """

    stripped = sentence_body.strip()

    words = list(WORD_PATTERN.finditer(stripped))

    if not words:
        return stripped

    word_values = [clean_word(match.group(0)) for match in words]

    # Find be-verb positions.
    be_indexes = [
        index for index, word in enumerate(word_values)
        if word in BE_VERBS
    ]

    # If this is a be-complement style sentence, insert "not" before the
    # replacement complement word.
    if be_indexes:
        return (
            stripped[:replacement_word_start]
            + "not "
            + stripped[replacement_word_start:]
        )

    # Fallback for non-be predicate forms.
    return "not " + stripped

def add_antonym_negation_to_question(
    sentence_body: str,
    replacement_word_start: int,
) -> str:
    """
    Adds the antonym-negation layer to a yes/no question.

    Examples:
    is sara bad? -> is sara not good?
    is sara not bad? -> is sara not not good?
    """

    stripped = sentence_body.strip()
    punctuation = ""

    if stripped.endswith("?"):
        punctuation = "?"
        stripped = stripped[:-1].strip()

    return (
        stripped[:replacement_word_start]
        + "not "
        + stripped[replacement_word_start:]
        + punctuation
    )


def rewrite_sentence_with_antonym(
    sentence: str,
    later_word_start_global: int,
    sentence_start_global: int,
    later_word: str,
    earlier_word: str,
    later_role: str,
) -> str:
    """
    Rewrites the whole atom/question containing the later antonym.

    Stage 1 intentionally creates a natural intermediate form:
    - Statement:
        ahmed is weak.
        -> ahmed is not strong.

    - Already-negated statement:
        not ahmed is weak.
        -> not ahmed is not strong.

    - Question:
        is khaled short?
        -> is khaled not tall?
    """

    original_sentence = sentence.strip()
    prefix, body = strip_numbering_prefix(original_sentence)

    prefix_len = len(prefix)
    local_word_start_in_sentence = later_word_start_global - sentence_start_global
    local_word_start_in_body = local_word_start_in_sentence - prefix_len
    local_word_end_in_body = local_word_start_in_body + len(later_word)

    replacement_word = adapt_earlier_word_for_later_context(
        earlier_word=earlier_word,
        later_word=later_word,
        later_role=later_role,
    )

    replaced_body = replace_word_span(
        sentence_body=body,
        word_start=local_word_start_in_body,
        word_end=local_word_end_in_body,
        replacement_word=replacement_word,
    )

    # After replacement, the replacement word begins at the same local start.
    replacement_word_start = local_word_start_in_body

    if sentence_is_question(replaced_body):
        rewritten_body = add_antonym_negation_to_question(
            sentence_body=replaced_body,
            replacement_word_start=replacement_word_start,
        )
    else:
        rewritten_body = add_antonym_negation_to_statement(
            sentence_body=replaced_body,
            replacement_word_start=replacement_word_start,
        )

    return prefix + rewritten_body


# ==================================================
# Occurrence extraction and rewrite search
# ==================================================

def extract_word_occurrences(text: str) -> List[Dict[str, Any]]:
    occurrences = []

    for sentence_start, sentence_end, sentence in split_sentence_spans(text):
        word_matches = list(WORD_PATTERN.finditer(sentence))
        sentence_words = [clean_word(match.group(0)) for match in word_matches]

        for word_index, match in enumerate(word_matches):
            word = match.group(0)
            cleaned = clean_word(word)

            if not cleaned or is_ignored_word(cleaned):
                continue

            role = infer_word_role(sentence_words, word_index)

            if role == "other":
                continue

            occurrences.append(
                {
                    "word": cleaned,
                    "start": sentence_start + match.start(),
                    "end": sentence_start + match.end(),
                    "role": role,
                    "sentence": sentence,
                    "sentence_start": sentence_start,
                    "sentence_end": sentence_end,
                }
            )

    return occurrences


def find_antonym_rewrites(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Finds later antonyms and rewrites their containing sentence/question.

    Important:
    - Exact same words are ignored.
      Example: open / open -> no rewrite.
    - Already rewritten later occurrences are not allowed to become canonical
      earlier words for later comparisons.
    """

    occurrences = extract_word_occurrences(text)
    rewrites = []
    changes = []
    rewritten_sentence_ranges = set()
    rewritten_occurrence_indexes = set()

    for later_index, later_occurrence in enumerate(occurrences):
        later_word = later_occurrence["word"]
        later_role = later_occurrence["role"]
        sentence_range = (
            later_occurrence["sentence_start"],
            later_occurrence["sentence_end"],
        )

        if sentence_range in rewritten_sentence_ranges:
            continue

        for earlier_index, earlier_occurrence in enumerate(occurrences[:later_index]):
            if earlier_index in rewritten_occurrence_indexes:
                continue

            earlier_word = earlier_occurrence["word"]

            # Exact same words are already unified.
            # They must not trigger antonym unification.
            if earlier_word == later_word:
                continue

            if are_direct_antonyms(earlier_word, later_word):
                replacement_sentence = rewrite_sentence_with_antonym(
                    sentence=later_occurrence["sentence"],
                    later_word_start_global=later_occurrence["start"],
                    sentence_start_global=later_occurrence["sentence_start"],
                    later_word=later_word,
                    earlier_word=earlier_word,
                    later_role=later_role,
                )

                rewrites.append(
                    {
                        "start": later_occurrence["sentence_start"],
                        "end": later_occurrence["sentence_end"],
                        "replacement": replacement_sentence,
                    }
                )

                changes.append(
                    {
                        "later_word": later_word,
                        "earlier_word": earlier_word,
                        "position": later_occurrence["start"],
                        "role": later_role,
                        "original_sentence": later_occurrence["sentence"].strip(),
                        "replacement_sentence_before_postprocessing": replacement_sentence,
                        "reason": "wordnet_direct_antonym",
                    }
                )

                rewritten_sentence_ranges.add(sentence_range)
                rewritten_occurrence_indexes.add(later_index)
                break

    return rewrites, changes


def apply_rewrites(text: str, rewrites: List[Dict[str, Any]]) -> str:
    updated = text

    for rewrite in sorted(rewrites, key=lambda item: item["start"], reverse=True):
        start = rewrite["start"]
        end = rewrite["end"]
        replacement = rewrite["replacement"]

        updated = updated[:start] + replacement + updated[end:]

    return updated


# ==================================================
# Main N8 function
# ==================================================
def n4_style_normalize_premise_body_for_n8(body: str) -> str:
    """
    Applies N4-style premise normalization for N8 debug/use.

    Handles normal cases:
        ahmed is not strong.
        -> not ahmed is strong.

    Handles outer-not cases:
        not ahmed is not strong.
        -> not not ahmed is strong.
    """

    body = ensure_period(body)
    stripped = body.strip()

    # Special case:
    # not <inner>
    # If inner itself normalizes to not X, preserve the outer not:
    # not ahmed is not strong.
    # inner = ahmed is not strong.
    # N4(inner) = not ahmed is strong.
    # result = not not ahmed is strong.
    if stripped.lower().startswith("not "):
        inner = stripped[4:].strip()
        inner = ensure_period(inner)

        inner_normalized = normalize_single_sentence_pattern(inner)

        if isinstance(inner_normalized, str) and inner_normalized.strip():
            return ensure_period("not " + inner_normalized.rstrip(".").strip())

        return body

    normalized = normalize_single_sentence_pattern(body)

    if isinstance(normalized, str) and normalized.strip():
        return normalized

    return body

def postprocess_rewritten_text_stage_2_n4_only(text: str) -> str:
    """
    Stage 2:
    Applies N4-style normalization only to premise lines.

    Questions are not passed through N4.
    """

    output_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            output_lines.append(raw_line)
            continue

        if stripped.lower() in {"premises:", "question:"}:
            output_lines.append(raw_line)
            continue

        leading_spaces = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        # Questions are not passed through N4.
        if stripped.endswith("?"):
            output_lines.append(raw_line)
            continue

        prefix, body = strip_numbering_prefix(stripped)
        processed_body = n4_style_normalize_premise_body_for_n8(body)
        processed = prefix + processed_body

        output_lines.append(leading_spaces + processed)

    return "\n".join(output_lines)


def postprocess_rewritten_text_stage_3_double_not_only(text: str) -> str:
    """
    Stage 3:
    Removes double negation from premise and question lines.

    Examples:
        not not ahmed is strong. -> ahmed is strong.
        is sara not not good? -> is sara good?
    """

    output_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            output_lines.append(raw_line)
            continue

        if stripped.lower() in {"premises:", "question:"}:
            output_lines.append(raw_line)
            continue

        leading_spaces = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        if stripped.endswith("?"):
            processed = simplify_question_double_negation(stripped)
        else:
            prefix, body = strip_numbering_prefix(stripped)
            body = collapse_adjacent_double_not(body)
            body = ensure_period(body)
            processed = prefix + body

        output_lines.append(leading_spaces + processed)

    return "\n".join(output_lines)

def unify_antonym_words(text: str) -> Dict[str, Any]:
    """
    Main N8 function.

    Debug stages:
    - stage_1_after_antonym_replacement:
      The prompt after replacing later antonym words with the earlier canonical word
      and adding the antonym negation layer.

    - stage_2_after_n4_premise_normalization:
      The prompt after applying N4-style normalization to rewritten premise lines.

    - stage_3_after_double_negation_cleanup:
      The final prompt after cancelling double negations.

    The returned "text" is always the final stage.
    """

    if not isinstance(text, str):
        return make_failure("Input must be a string.")

    if not text.strip():
        return make_failure("Empty input.")

    if not wordnet_is_available():
        return make_failure(
            "NLTK WordNet is not available. Run: "
            "python -c \"import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')\""
        )

    rewrites, changes = find_antonym_rewrites(text)

    if not rewrites:
        return {
            "success": True,
            "text": text,
            "changes": [],
            "error": None,
            "debug": {
                "triggered": False,
                "stage_1_after_antonym_replacement": text,
                "stage_2_after_n4_premise_normalization": text,
                "stage_3_after_double_negation_cleanup": text,
            },
        }

    stage_1_text = apply_rewrites(text, rewrites)

    stage_2_text = postprocess_rewritten_text_stage_2_n4_only(stage_1_text)

    stage_3_text = postprocess_rewritten_text_stage_3_double_not_only(stage_2_text)

    for change in changes:
        change["stage_1_after_antonym_replacement"] = stage_1_text
        change["stage_2_after_n4_premise_normalization"] = stage_2_text
        change["stage_3_after_double_negation_cleanup"] = stage_3_text
        change["final_text_after_postprocessing"] = stage_3_text

    return {
        "success": True,
        "text": stage_3_text,
        "changes": changes,
        "error": None,
        "debug": {
            "triggered": True,
            "stage_1_after_antonym_replacement": stage_1_text,
            "stage_2_after_n4_premise_normalization": stage_2_text,
            "stage_3_after_double_negation_cleanup": stage_3_text,
        },
    }