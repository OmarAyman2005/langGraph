"""
N8 — Antonym Words Unifier.

Purpose:
- Takes the normalized prompt after N7.
- Detects direct antonym words using NLTK WordNet only.
- Keeps the earlier occurring word.
- Rewrites later antonym atoms/questions as negations of the earlier word form.
- Performs no LLM calls.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from normalizer.semantic_lexicon import (
    are_direct_antonyms,
    get_best_base_form,
    wordnet_is_available,
)


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


def clean_word(word: str) -> str:
    return word.lower().strip()


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


def replace_word_span(sentence_body: str, word_start: int, word_end: int, replacement_word: str) -> str:
    return sentence_body[:word_start] + replacement_word + sentence_body[word_end:]


def add_negation_to_statement(sentence_body: str) -> str:
    stripped = sentence_body.strip()

    if stripped.startswith("not "):
        return stripped

    return "not " + stripped


def add_negation_to_question(sentence_body: str) -> str:
    """
    is the door open? -> is the door not open?
    does sara pass? -> does sara not pass?
    """

    stripped = sentence_body.strip()
    punctuation = ""

    if stripped.endswith("?"):
        punctuation = "?"
        stripped = stripped[:-1].strip()

    words = list(WORD_PATTERN.finditer(stripped))

    if not words:
        return sentence_body

    word_values = [clean_word(match.group(0)) for match in words]

    if "not" in word_values:
        return sentence_body

    first_word = word_values[0]

    if first_word in BE_VERBS or first_word in DO_AUXILIARIES:
        last_match = words[-1]
        return stripped[:last_match.start()] + "not " + stripped[last_match.start():] + punctuation

    return sentence_body


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

    if sentence_is_question(replaced_body):
        rewritten_body = add_negation_to_question(replaced_body)
    else:
        rewritten_body = add_negation_to_statement(replaced_body)

    return prefix + rewritten_body


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
    If a later occurrence is rewritten, it is not allowed to become the canonical
    earlier word for later comparisons. This prevents:
    open -> closed rewrite, then closed -> open rewrite in the question.
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
                        "replacement_sentence": replacement_sentence,
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


def unify_antonym_words(text: str) -> Dict[str, Any]:
    """
    Main N8 function.
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
        return make_success(text=text, changes=[])

    updated_text = apply_rewrites(text, rewrites)

    return make_success(text=updated_text, changes=changes)