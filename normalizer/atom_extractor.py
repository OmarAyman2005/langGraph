import re
from typing import Any, Dict, List, Tuple


def parse_sentence_pattern(sentence: str) -> Dict[str, Any]:
    s = sentence.strip().rstrip(".")
    lowered = s.lower()

    if lowered.startswith("if ") and ", then " in lowered:
        parts = re.split(r",\s*then\s*", s, maxsplit=1, flags=re.IGNORECASE)
        return {
            "pattern": "conditional",
            "atoms": [parts[0][3:].strip(), parts[1].strip()],
        }

    if lowered.startswith("not "):
        return {
            "pattern": "negation",
            "atoms": [s[4:].strip()],
        }

    if " or " in lowered:
        parts = re.split(r"\s+or\s+", s, maxsplit=1, flags=re.IGNORECASE)
        return {
            "pattern": "disjunction",
            "atoms": [parts[0].strip(), parts[1].strip()],
        }

    if " and " in lowered:
        parts = re.split(r"\s+and\s+", s, maxsplit=1, flags=re.IGNORECASE)
        return {
            "pattern": "conjunction",
            "atoms": [parts[0].strip(), parts[1].strip()],
        }

    return {
        "pattern": "fact",
        "atoms": [s.strip()],
    }


def verb_to_third_person(verb: str) -> str:
    lower = verb.lower()

    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return verb[:-1] + "ies"

    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"

    return verb + "s"


def convert_question_to_target_candidates(question: str) -> List[str]:
    q = question.strip().rstrip("?").strip()
    words = q.split()

    if len(words) < 2:
        return []

    aux = words[0].lower()
    rest_words = words[1:]

    if aux in {"is", "are", "am", "was", "were"}:
        if len(rest_words) < 2:
            return [" ".join(rest_words)]

        if "not" in [w.lower() for w in rest_words]:
            not_index = [w.lower() for w in rest_words].index("not")
            subject = " ".join(rest_words[:not_index])
            predicate = " ".join(rest_words[not_index + 1 :])
            return [f"not {subject} {aux} {predicate}"]

        if len(rest_words) >= 3 and rest_words[1].lower() in {"a", "an", "the"}:
            subject = rest_words[0]
            predicate = " ".join(rest_words[1:])
        else:
            subject = " ".join(rest_words[:-1])
            predicate = rest_words[-1]

        return [f"{subject} {aux} {predicate}"]

    if aux in {
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
    }:
        return [" ".join(rest_words[:1] + [words[0].lower()] + rest_words[1:])]

    if aux in {"do", "does"}:
        if len(rest_words) < 2:
            return [" ".join(rest_words)]

        # Handle common particle/preposition verb phrases:
        # "wake up", "turn on", "shut down", etc.
        particles = {"up", "on", "off", "down", "out", "in", "over", "away", "back"}

        if len(rest_words) >= 3 and rest_words[-1].lower() in particles:
            subject_words = rest_words[:-2]
            verb_phrase_words = rest_words[-2:]
        else:
            subject_words = rest_words[:-1]
            verb_phrase_words = rest_words[-1:]

        subject = " ".join(subject_words)
        verb_phrase = " ".join(verb_phrase_words)

        if aux == "does":
            first_verb = verb_phrase_words[0]
            rest_of_verb = verb_phrase_words[1:]

            proposition_without_do = " ".join(
                [subject, verb_to_third_person(first_verb)] + rest_of_verb
            )
        else:
            proposition_without_do = " ".join([subject] + verb_phrase_words)

        proposition_with_do = " ".join([subject, aux] + verb_phrase_words)

        return [proposition_without_do, proposition_with_do]

    if aux == "did":
        if len(rest_words) < 2:
            return [" ".join(rest_words)]

        subject = rest_words[0]
        verb = rest_words[1]
        after = rest_words[2:]

        proposition_with_did = " ".join([subject, "did", verb] + after)
        return [proposition_with_did]

    return [" ".join(rest_words)]


def create_atom_table(
    normalized_premises: List[str],
    question: str,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    atom_table = []
    premise_structures = []

    counter = 1

    for premise_index, sentence in enumerate(normalized_premises, start=1):
        parsed = parse_sentence_pattern(sentence)
        atom_ids = []

        for atom in parsed["atoms"]:
            atom_id = f"A{counter}"
            counter += 1
            atom_ids.append(atom_id)

            atom_table.append(
                {
                    "id": atom_id,
                    "text": atom,
                    "source": f"P{premise_index}",
                }
            )

        premise_structures.append(
            {
                "premise_id": f"P{premise_index}",
                "pattern": parsed["pattern"],
                "atom_ids": atom_ids,
            }
        )

    question_candidates = convert_question_to_target_candidates(question)
    question_atom_ids = []

    for candidate in question_candidates:
        atom_id = f"Q{len(question_atom_ids) + 1}"
        question_atom_ids.append(atom_id)

        atom_table.append(
            {
                "id": atom_id,
                "text": candidate,
                "source": "question",
            }
        )

    metadata = {
        "premise_structures": premise_structures,
        "question_atom_ids": question_atom_ids,
        "original_question": question,
    }

    return atom_table, metadata


def base_verb_from_third_person(verb: str) -> str:
    lower = verb.lower()

    if lower.endswith("ies"):
        return verb[:-3] + "y"

    if lower.endswith(("sses", "shes", "ches", "xes", "zes", "oes")):
        return verb[:-2]

    if lower.endswith("s") and len(verb) > 1:
        return verb[:-1]

    return verb


def normalize_question_subject_case(subject: str) -> str:
    if not subject:
        return subject

    words = subject.split()

    # Lowercase pronoun/article at the start of a question.
    if words[0] in {"The", "A", "An", "It"}:
        words[0] = words[0].lower()
        return " ".join(words)

    # Keep likely proper names unchanged: Ahmed -> Ahmed
    return subject


def choose_do_aux(subject: str) -> str:
    s = subject.lower().strip()
    plural_heads = {"i", "you", "we", "they", "people"}
    if s in plural_heads:
        return "Do"
    if s.startswith(("the ", "a ", "an ")):
        return "Does"
    return "Does"


def proposition_to_question(proposition: str) -> str:
    p = proposition.strip().rstrip(".")
    lower = p.lower()

    # Handle canonical negation form: "not X"
    if lower.startswith("not "):
        inner = p[4:].strip()
        inner_lower = inner.lower()

        for marker in [" is ", " are ", " was ", " were "]:
            if marker in inner_lower:
                idx = inner_lower.index(marker)
                subject = inner[:idx]
                rest = inner[idx + len(marker) :]
                aux = marker.strip()
                return f"{aux.capitalize()} {normalize_question_subject_case(subject)} not {rest}?"

        return f"Is it not true that {inner}?"

    # be-verb forms
    for marker in [" is not ", " are not ", " was not ", " were not "]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker) :]
            aux = marker.strip().split()[0]
            return f"{aux.capitalize()} {subject} not {rest}?"

    for marker in [" is ", " are ", " was ", " were "]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker) :]
            aux = marker.strip()
            return (
                f"{aux.capitalize()} {normalize_question_subject_case(subject)} {rest}?"
            )

    # modal / have forms
    for marker in [
        " has ",
        " have ",
        " had ",
        " will ",
        " can ",
        " could ",
        " should ",
        " would ",
        " must ",
    ]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker) :]
            aux = marker.strip()
            return f"{aux.capitalize()} {subject} {rest}?"

    words = p.split()

    # find first likely third-person verb ending in s after at least one subject word
    for i in range(1, len(words)):
        word = words[i]
        lw = word.lower()

        if (
            lw.endswith("s")
            and lw not in {"is", "was", "has"}
            and not lw.endswith("ss")
        ):
            subject = " ".join(words[:i])
            verb = base_verb_from_third_person(word)
            rest = " ".join(words[i + 1 :])
            subject_norm = normalize_question_subject_case(subject)
            aux = choose_do_aux(subject_norm)
            return f"{aux} {subject_norm} {verb}{(' ' + rest) if rest else ''}?"

    if words:
        subject = words[0]
        rest = " ".join(words[1:])
        aux = choose_do_aux(subject)
        return f"{aux} {subject}{(' ' + rest) if rest else ''}?"

    return f"Does {p}?"
