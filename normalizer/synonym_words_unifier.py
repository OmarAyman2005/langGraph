"""
N7 — Synonym Words Unifier.

Purpose:
- Takes the semi-normalized prompt after N6.
- Detects direct synonym words using NLTK WordNet only.
- Keeps the earlier occurring synonym.
- Replaces later synonyms with the earlier synonym, while avoiding unsafe subject/object noun rewrites.
- Performs no LLM calls.

Important scope:
- This component is word-level, but conservative.
- It mainly rewrites likely predicate words:
  1. words after be-verbs: is/are/am/was/were
  2. words after do/does/did in questions
  3. simple predicate verbs after a subject
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from normalizer.semantic_lexicon import (
    are_direct_synonyms,
    get_best_base_form,
    wordnet_is_available,
)


WORD_PATTERN = re.compile(r"\b[a-zA-Z]+\b")


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

    # Normalized prompt section labels.
    "premises",
    "question",
}

SECTION_LABELS = {"premises", "question"}
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
    Splits text into rough sentence spans while keeping offsets.

    It also allows normalized prompt sections like:
    Premises:
    1. ...
    Question:
    ...
    """

    spans = []
    start = 0

    for match in re.finditer(r"[.!?]", text):
        end = match.end()
        sentence = text[start:end].strip()

        if sentence:
            leading_spaces = len(text[start:end]) - len(text[start:end].lstrip())
            real_start = start + leading_spaces
            spans.append((real_start, end, text[real_start:end]))

        start = end

    if start < len(text):
        sentence = text[start:].strip()

        if sentence:
            leading_spaces = len(text[start:]) - len(text[start:].lstrip())
            real_start = start + leading_spaces
            spans.append((real_start, len(text), text[real_start:]))

    return spans


def get_local_sentence_words(sentence_words: List[str], word_index: int) -> tuple[List[str], int]:
    """
    Removes leading normalized-prompt section labels from role analysis.

    Example:
    ["question", "does", "sara", "begin"] with index 3
    becomes:
    ["does", "sara", "begin"] with local index 2
    """

    if sentence_words and sentence_words[0] in SECTION_LABELS:
        return sentence_words[1:], word_index - 1

    return sentence_words, word_index


def last_content_word_index(words: List[str], start_index: int = 0) -> int | None:
    """
    Returns the index of the last non-ignored content word at or after start_index.
    """

    for index in range(len(words) - 1, start_index - 1, -1):
        if words[index] not in FUNCTION_WORDS_TO_IGNORE:
            return index

    return None


def infer_word_role(sentence_words: List[str], word_index: int) -> str:
    """
    Infers a rough role for the word in a simple normalized sentence.

    Returns:
    - be_complement: likely adjective/state complement
    - do_question_predicate: predicate after do/does/did
    - simple_predicate: likely main predicate after subject
    - other: likely subject/object/unsafe
    """

    local_words, local_index = get_local_sentence_words(sentence_words, word_index)

    if local_index <= 0 or local_index >= len(local_words):
        return "other"

    previous_word = local_words[local_index - 1]

    # Direct be-complement pattern:
    # ahmed is happy.
    if previous_word in BE_VERBS:
        return "be_complement"

    # Be-question or be-statement with multi-word subject:
    # is the bag large?
    # the solution is right.
    # Mark only the final content word after the be-verb as complement.
    be_indexes = [i for i, word in enumerate(local_words) if word in BE_VERBS]

    if be_indexes:
        first_be_index = be_indexes[0]
        final_content_index = last_content_word_index(local_words, start_index=first_be_index + 1)

        if final_content_index is not None and local_index == final_content_index:
            return "be_complement"

        return "other"

    # Question form:
    # does sara begin?
    # If there is a do/does/did auxiliary, only the final content word after it
    # is treated as the predicate.
    do_indexes = [i for i, word in enumerate(local_words) if word in DO_AUXILIARIES]

    if do_indexes:
        first_do_index = do_indexes[0]
        final_content_index = last_content_word_index(local_words, start_index=first_do_index + 1)

        if final_content_index is not None and local_index == final_content_index:
            return "do_question_predicate"

        return "other"

    # Simple statement:
    # ahmed starts.
    if local_index == 1:
        return "simple_predicate"

    # Article subject form without be-verb:
    # the match starts.
    if (
        len(local_words) >= 3
        and local_words[0] in {"the", "a", "an"}
        and local_index == 2
    ):
        return "simple_predicate"

    return "other"


def extract_word_occurrences(text: str) -> List[Dict[str, Any]]:
    occurrences = []

    for sentence_start, _sentence_end, sentence in split_sentence_spans(text):
        word_matches = list(WORD_PATTERN.finditer(sentence))
        sentence_words = [clean_word(match.group(0)) for match in word_matches]

        for word_index, match in enumerate(word_matches):
            word = match.group(0)
            cleaned = clean_word(word)

            if not cleaned or is_ignored_word(cleaned):
                continue

            role = infer_word_role(sentence_words, word_index)

            # Conservative scope: only rewrite likely predicates.
            if role == "other":
                continue

            occurrences.append(
                {
                    "word": cleaned,
                    "start": sentence_start + match.start(),
                    "end": sentence_start + match.end(),
                    "role": role,
                    "sentence": sentence,
                }
            )

    return occurrences


def inflect_third_person_singular(base: str) -> str:
    base = clean_word(base)

    if not base:
        return base

    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ies"

    if base.endswith(("s", "sh", "ch", "x", "z", "o")):
        return base + "es"

    return base + "s"


def inflect_past_simple(base: str) -> str:
    base = clean_word(base)

    if not base:
        return base

    irregular_past = {
        "begin": "began",
        "start": "started",
        "run": "ran",
        "win": "won",
        "lose": "lost",
        "buy": "bought",
        "choose": "chose",
        "go": "went",
        "come": "came",
        "write": "wrote",
        "speak": "spoke",
        "take": "took",
        "give": "gave",
    }

    if base in irregular_past:
        return irregular_past[base]

    if base.endswith("e"):
        return base + "d"

    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ied"

    return base + "ed"


def inflect_present_participle(base: str) -> str:
    base = clean_word(base)

    if not base:
        return base

    if base.endswith("ie"):
        return base[:-2] + "ying"

    if base.endswith("e") and not base.endswith("ee"):
        return base[:-1] + "ing"

    return base + "ing"


def adapt_replacement_to_later_form(
    earlier_word: str,
    later_word: str,
    later_role: str,
) -> str:
    """
    Keeps the earlier word's meaning but adapts simple morphology to fit the later word's context.
    """

    earlier = clean_word(earlier_word)
    later = clean_word(later_word)

    if not earlier or not later:
        return earlier

    # For adjective/state complements, preserve exact earlier surface.
    if later_role == "be_complement":
        return earlier

    earlier_base = get_best_base_form(earlier)
    later_base = get_best_base_form(later)

    # In do/does/did questions, use base form.
    if later_role == "do_question_predicate":
        return earlier_base

    if later == later_base:
        return earlier_base

    if later.endswith("ing"):
        return inflect_present_participle(earlier_base)

    if later.endswith("ed") or later in {
        "began",
        "ran",
        "won",
        "lost",
        "bought",
        "chose",
        "went",
        "came",
        "wrote",
        "spoke",
        "took",
        "gave",
    }:
        return inflect_past_simple(earlier_base)

    if later.endswith("s"):
        return inflect_third_person_singular(earlier_base)

    return earlier


def find_synonym_replacements(text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Finds later predicate words that should be replaced by earlier synonym predicate words.

    Returns:
    - replacements: span-level replacements
    - changes: human-readable change records
    """

    occurrences = extract_word_occurrences(text)
    replacements = []
    changes = []

    for later_index, later_occurrence in enumerate(occurrences):
        later_word = later_occurrence["word"]
        later_role = later_occurrence["role"]

        for earlier_occurrence in occurrences[:later_index]:
            earlier_word = earlier_occurrence["word"]

            if earlier_word == later_word:
                continue

            if are_direct_synonyms(earlier_word, later_word):
                replacement_word = adapt_replacement_to_later_form(
                    earlier_word=earlier_word,
                    later_word=later_word,
                    later_role=later_role,
                )

                replacements.append(
                    {
                        "start": later_occurrence["start"],
                        "end": later_occurrence["end"],
                        "replacement": replacement_word,
                    }
                )

                changes.append(
                    {
                        "later_word": later_word,
                        "earlier_word": earlier_word,
                        "replacement_word": replacement_word,
                        "position": later_occurrence["start"],
                        "role": later_role,
                        "reason": "wordnet_direct_synonym",
                    }
                )

                break

    return replacements, changes


def apply_replacements(text: str, replacements: List[Dict[str, Any]]) -> str:
    """
    Applies span replacements from right to left so indexes stay valid.
    """

    updated = text

    for replacement in sorted(replacements, key=lambda item: item["start"], reverse=True):
        start = replacement["start"]
        end = replacement["end"]
        replacement_text = replacement["replacement"]

        updated = updated[:start] + replacement_text + updated[end:]

    return updated


def unify_synonym_words(text: str) -> Dict[str, Any]:
    """
    Main N7 function.
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

    replacements, changes = find_synonym_replacements(text)

    if not replacements:
        return make_success(text=text, changes=[])

    updated_text = apply_replacements(text, replacements)

    return make_success(text=updated_text, changes=changes)