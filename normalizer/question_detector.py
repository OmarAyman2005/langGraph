import re
from typing import List, Tuple, Dict, Any

from normalizer.constants import AUXILIARIES, WH_WORDS


def first_word(text: str) -> str:
    words = re.findall(r"[A-Za-z]+", text.strip())
    return words[0].lower() if words else ""


def split_candidate_clauses(raw_input: str) -> List[str]:
    """
    Deterministic clause detection.
    Uses line breaks first, then punctuation as fallback.
    """
    lines = [line.strip() for line in raw_input.splitlines() if line.strip()]

    if len(lines) > 1:
        return lines

    parts = re.split(r"[?.!]+", raw_input)
    return [p.strip() for p in parts if p.strip()]


def _is_likely_subject_start(word: str) -> bool:
    """
    Heuristic for whether a word can start a subject after an auxiliary.

    Examples:
    - Is Ahmed tired
    - Is the ground wet
    - Does Ahmed pass
    - Will the machine start
    """
    if not word:
        return False

    lowered = word.lower()

    if lowered in {
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "this",
        "that",
        "these",
        "those",
        "the",
        "a",
        "an",
    }:
        return True

    # Proper-name-like or normal noun-like word.
    return bool(re.match(r"^[A-Za-z]+$", word))


def _looks_like_inline_yes_no_question(words: List[str], start_index: int) -> bool:
    """
    Check whether words[start_index:] can plausibly begin with:
    Auxiliary + Subject + Predicate/Rest

    This is intentionally heuristic, because punctuation may be missing.
    """
    if start_index >= len(words):
        return False

    aux = words[start_index].lower()

    if aux not in AUXILIARIES:
        return False

    # Need at least: auxiliary + subject + something
    if start_index + 2 >= len(words):
        return False

    next_word = words[start_index + 1]

    if not _is_likely_subject_start(next_word):
        return False

    return True


def _tokenize_with_spans(text: str) -> List[Tuple[str, int, int]]:
    """
    Return alphabetic tokens with character spans.
    """
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[A-Za-z]+", text)]


def detect_inline_question_sequences(raw_input: str) -> Tuple[List[str], List[Tuple[int, int]]]:
    """
    Detect yes/no question sequences anywhere in the raw input.

    This supports punctuation-free cases like:
    Ahmed Played Menna Cried if Ahmed Won Talaat Wins is Talaat winning

    Detected question:
    is Talaat winning
    """
    tokens = _tokenize_with_spans(raw_input)
    words = [tok[0] for tok in tokens]

    candidates: List[Tuple[str, int, int]] = []

    for i, word in enumerate(words):
        lowered = word.lower()

        if lowered not in AUXILIARIES:
            continue

        if not _looks_like_inline_yes_no_question(words, i):
            continue

        # If this auxiliary is preceded by a WH word nearby, it is not a yes/no question.
        # Example: "what does Ahmed do"
        previous_window = [w.lower() for w in words[max(0, i - 3):i]]
        if any(w in WH_WORDS for w in previous_window):
            continue

        start_char = tokens[i][1]

        # By default, an inline detected question extends to the end of the prompt.
        # This matches the normal use case where the question is the final sequence.
        end_char = len(raw_input)

        question_text = raw_input[start_char:end_char].strip()

        if question_text:
            candidates.append((question_text, start_char, end_char))

    # Keep only the most plausible inline candidate:
    # the last auxiliary-led sequence in the prompt.
    #
    # This avoids incorrectly counting internal auxiliary words when a later one is
    # the actual question.
    if not candidates:
        return [], []

    last_question, start, end = candidates[-1]
    return [last_question], [(start, end)]


def detect_wh_question_sequences(raw_input: str) -> List[str]:
    """
    Detect WH-style question sequences anywhere in the input.

    Examples:
    - what does Ahmed do
    - why is Ahmed tired
    - how can Sara win
    """
    lowered_words = [w.lower() for w, _, _ in _tokenize_with_spans(raw_input)]

    found = []

    for i, word in enumerate(lowered_words):
        if word not in WH_WORDS:
            continue

        # WH followed shortly by an auxiliary strongly indicates a WH question.
        lookahead = lowered_words[i + 1:i + 5]
        if any(w in AUXILIARIES for w in lookahead):
            found.append(word)

    return found


def detect_yes_no_questions(raw_input: str) -> Tuple[List[str], List[str]]:
    """
    Detect yes/no questions and return:
    - list of detected yes/no questions
    - list of remaining candidate premise clauses
    """

    # 1. Explicit question-mark based detection.
    explicit_iter = list(re.finditer(r"[^.?!\n]*\?", raw_input))

    if explicit_iter:
        questions = []
        non_questions = []

        qs = []
        spans = []

        for m in explicit_iter:
            qtext = m.group(0).strip()
            if qtext:
                qs.append(qtext)
                spans.append((m.start(), m.end()))

        for q in qs:
            if first_word(q) in AUXILIARIES:
                questions.append(q)
            else:
                non_questions.append(q)

        pieces = []
        last = 0

        for s, e in spans:
            pieces.append(raw_input[last:s])
            last = e

        pieces.append(raw_input[last:])
        remaining = " ".join(pieces).strip()

        remaining_clauses = [
            c.strip()
            for c in split_candidate_clauses(remaining)
            if c.strip()
        ]

        non_questions = remaining_clauses + non_questions

        return questions, non_questions

    # 2. Normal clause-start detection.
    clauses = split_candidate_clauses(raw_input)

    questions = []
    non_questions = []

    for clause in clauses:
        fw = first_word(clause)
        if fw in AUXILIARIES:
            questions.append(clause.strip())
        else:
            non_questions.append(clause.strip())

    if questions:
        return questions, non_questions

    # 3. Inline punctuation-free sequence detection.
    inline_questions, spans = detect_inline_question_sequences(raw_input)

    if inline_questions:
        pieces = []
        last = 0

        for s, e in spans:
            pieces.append(raw_input[last:s])
            last = e

        pieces.append(raw_input[last:])
        remaining = " ".join(pieces).strip()

        remaining_clauses = [
            c.strip()
            for c in split_candidate_clauses(remaining)
            if c.strip()
        ]

        return inline_questions, remaining_clauses

    return [], non_questions


def detect_question_form_starts(raw_input: str) -> List[Tuple[str, str]]:
    """
    Detect question-form starts anywhere in the prompt.

    Returns:
    [("wh", "what"), ("yes_no", "does"), ...]
    """

    found: List[Tuple[str, str]] = []

    # WH questions anywhere.
    for wh in detect_wh_question_sequences(raw_input):
        found.append(("wh", wh))

    # Yes/no questions.
    questions, _ = detect_yes_no_questions(raw_input)

    for q in questions:
        fw = first_word(q)
        if fw in AUXILIARIES:
            found.append(("yes_no", fw))

    return found


def detect_single_yes_no_question(raw_input: str) -> Dict[str, Any]:
    if not raw_input or not raw_input.strip():
        return {
            "success": False,
            "question": None,
            "candidate_premise_text": None,
            "error": "Empty input",
        }

    question_forms = detect_question_form_starts(raw_input)

    yes_no_count = sum(1 for kind, _ in question_forms if kind == "yes_no")
    wh_count = sum(1 for kind, _ in question_forms if kind == "wh")

    errors = []

    if yes_no_count == 0:
        errors.append("No yes/no question detected")

    if yes_no_count > 1:
        errors.append("More than one yes/no question detected")

    if wh_count > 0:
        errors.append("Non yes/no question detected")

    if errors:
        return {
            "success": False,
            "question": None,
            "candidate_premise_text": None,
            "error": "\n".join(errors),
        }

    questions, non_questions = detect_yes_no_questions(raw_input)

    if len(questions) == 0:
        return {
            "success": False,
            "question": None,
            "candidate_premise_text": None,
            "error": "No yes/no question detected",
        }

    if len(questions) > 1:
        return {
            "success": False,
            "question": None,
            "candidate_premise_text": None,
            "error": "More than one yes/no question detected",
        }

    raw_question = questions[0].strip()
    candidate_premise_text = "\n".join(non_questions).strip()

    if not candidate_premise_text:
        return {
            "success": False,
            "question": None,
            "candidate_premise_text": None,
            "error": "No candidate premises found",
        }

    return {
        "success": True,
        "question": raw_question,
        "candidate_premise_text": candidate_premise_text,
        "error": None,
    }