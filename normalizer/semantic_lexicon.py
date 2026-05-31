"""
Semantic Lexicon for the Normalizer.

Used by:
- N7: Synonym Words Unifier
- N8: Antonym Words Unifier

Current experimental design:
- Use NLTK WordNet only.
- No local/manual synonym lists.
- No local/manual antonym lists.
- No LLM calls.

This file only detects word relations.
It does not rewrite prompts.
"""

from __future__ import annotations

from functools import lru_cache


try:
    from nltk.corpus import wordnet as wn
except Exception:
    wn = None


WORDNET_POS_TAGS = ["n", "v", "a", "r"]


def normalize_word(word: str) -> str:
    return word.lower().strip()


@lru_cache(maxsize=1)
def wordnet_is_available() -> bool:
    """
    Checks whether NLTK WordNet is installed and whether its data exists.
    """

    if wn is None:
        return False

    try:
        wn.synsets("test")
        return True
    except LookupError:
        return False
    except Exception:
        return False


@lru_cache(maxsize=4096)
def get_wordnet_base_forms(word: str) -> set[str]:
    """
    Returns possible WordNet base forms for a word.

    Examples:
    starts -> start
    begins -> begin
    studies -> study
    """

    word = normalize_word(word)

    if not word or not wordnet_is_available():
        return {word} if word else set()

    forms = {word}

    try:
        for pos in WORDNET_POS_TAGS:
            base = wn.morphy(word, pos=pos)

            if base:
                forms.add(normalize_word(base))

    except Exception:
        pass

    return {form for form in forms if form}


@lru_cache(maxsize=4096)
def get_wordnet_synonyms(word: str) -> set[str]:
    """
    Returns WordNet synonyms for a single word.

    Notes:
    - Multi-word lemmas are ignored because N7/N8 are word-level.
    - The original word and its base forms are removed.
    """

    word = normalize_word(word)

    if not word or not wordnet_is_available():
        return set()

    synonyms: set[str] = set()
    query_forms = get_wordnet_base_forms(word)

    try:
        for query in query_forms:
            for synset in wn.synsets(query):
                for lemma in synset.lemmas():
                    lemma_name = normalize_word(lemma.name().replace("_", " "))

                    if " " in lemma_name:
                        continue

                    synonyms.add(lemma_name)

    except Exception:
        return set()

    synonyms -= query_forms
    synonyms.discard(word)

    return synonyms


@lru_cache(maxsize=4096)
def get_wordnet_antonyms(word: str) -> set[str]:
    """
    Returns WordNet antonyms for a single word.

    Notes:
    - Multi-word lemmas are ignored because N7/N8 are word-level.
    - The original word and its base forms are removed.
    """

    word = normalize_word(word)

    if not word or not wordnet_is_available():
        return set()

    antonyms: set[str] = set()
    query_forms = get_wordnet_base_forms(word)

    try:
        for query in query_forms:
            for synset in wn.synsets(query):
                for lemma in synset.lemmas():
                    for antonym in lemma.antonyms():
                        antonym_name = normalize_word(antonym.name().replace("_", " "))

                        if " " in antonym_name:
                            continue

                        antonyms.add(antonym_name)

    except Exception:
        return set()

    antonyms -= query_forms
    antonyms.discard(word)

    return antonyms


def get_direct_synonyms(word: str) -> set[str]:
    """
    Returns direct WordNet synonyms for a word.
    """

    word = normalize_word(word)

    if not word:
        return set()

    results = get_wordnet_synonyms(word)
    results.discard(word)

    return results


def get_direct_antonyms(word: str) -> set[str]:
    """
    Returns direct WordNet antonyms for a word.
    """

    word = normalize_word(word)

    if not word:
        return set()

    results = get_wordnet_antonyms(word)
    results.discard(word)

    return results


def are_direct_synonyms(word_a: str, word_b: str) -> bool:
    """
    Returns True if word_a and word_b are direct synonyms according to WordNet.

    The check also considers WordNet base forms, so pairs like:
    starts / begins
    started / began
    may still be detected through start / begin.
    """

    a = normalize_word(word_a)
    b = normalize_word(word_b)

    if not a or not b or a == b:
        return False

    forms_a = get_wordnet_base_forms(a)
    forms_b = get_wordnet_base_forms(b)

    for form_a in forms_a:
        synonyms_a = get_wordnet_synonyms(form_a)

        if forms_b & synonyms_a:
            return True

    for form_b in forms_b:
        synonyms_b = get_wordnet_synonyms(form_b)

        if forms_a & synonyms_b:
            return True

    return False


def are_direct_antonyms(word_a: str, word_b: str) -> bool:
    """
    Returns True if word_a and word_b are direct antonyms according to WordNet.
    """

    a = normalize_word(word_a)
    b = normalize_word(word_b)

    if not a or not b or a == b:
        return False

    forms_a = get_wordnet_base_forms(a)
    forms_b = get_wordnet_base_forms(b)

    for form_a in forms_a:
        antonyms_a = get_wordnet_antonyms(form_a)

        if forms_b & antonyms_a:
            return True

    for form_b in forms_b:
        antonyms_b = get_wordnet_antonyms(form_b)

        if forms_a & antonyms_b:
            return True

    return False


def get_best_base_form(word: str) -> str:
    """
    Returns a reasonable WordNet base form for morphology adaptation.
    Prefer verb base form when available, then any WordNet base form, then the original word.
    """

    word = normalize_word(word)

    if not word:
        return word

    if wordnet_is_available():
        try:
            verb_base = wn.morphy(word, pos="v")

            if verb_base:
                return normalize_word(verb_base)

            for pos in WORDNET_POS_TAGS:
                base = wn.morphy(word, pos=pos)

                if base:
                    return normalize_word(base)

        except Exception:
            pass

    return word


def describe_word_relations(word: str) -> dict:
    """
    Debug helper for manual checks.
    """

    word = normalize_word(word)

    return {
        "word": word,
        "wordnet_available": wordnet_is_available(),
        "base_forms": sorted(get_wordnet_base_forms(word)),
        "synonyms": sorted(get_direct_synonyms(word)),
        "antonyms": sorted(get_direct_antonyms(word)),
    }