import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports for LLM-related classes to avoid import-time failures
SystemMessage = None
HumanMessage = None
ChatOllama = None

from prompts import (
    PREMISE_SEGMENTATION_PROMPT,
    PREMISE_NORMALIZATION_PROMPT,
    ATOM_RELATION_PROMPT,
)


AUXILIARIES = {
    "is", "are", "am", "was", "were",
    "do", "does", "did",
    "has", "have", "had",
    "will", "would",
    "can", "could",
    "shall", "should",
    "may", "might",
    "must",
}


def make_error(reason: str) -> Dict[str, Any]:
    return {
        "success": False,
        "normalized_input": None,
        "error": f"NORMALIZATION_ERROR: {reason}",
        "debug": {},
    }


def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"LLM did not return valid JSON: {text}")

    return json.loads(cleaned[start:end + 1])


def call_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    try:
        # local import to avoid hard dependency at module import time
        from langchain_core.messages import SystemMessage as _SystemMessage, HumanMessage as _HumanMessage
        from langchain_ollama import ChatOllama as _ChatOllama

        llm = _ChatOllama(model="llama3.1:8b", temperature=0)

        response = llm.invoke(
            [
                _SystemMessage(content=system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )

        return extract_json(response.content)
    except Exception as e:
        # Bubble up a clear exception so callers can decide fallback behavior.
        raise RuntimeError(f"LLM call failed: {e}")


def first_word(text: str) -> str:
    words = re.findall(r"[A-Za-z]+", text.strip())
    return words[0].lower() if words else ""


def split_candidate_clauses(raw_input: str) -> List[str]:
    """
    V1 deterministic clause detection.
    Uses line breaks first, then punctuation as fallback.
    The LLM is used later for premise segmentation.
    """
    lines = [line.strip() for line in raw_input.splitlines() if line.strip()]

    if len(lines) > 1:
        return lines

    # fallback if user wrote everything in one line
    parts = re.split(r"[?.!]+", raw_input)
    return [p.strip() for p in parts if p.strip()]


def detect_yes_no_questions(raw_input: str) -> Tuple[List[str], List[str]]:
    # First, try simple clause splitting
    clauses = split_candidate_clauses(raw_input)

    questions = []
    non_questions = []

    for clause in clauses:
        fw = first_word(clause)
        if fw in AUXILIARIES:
            questions.append(clause.strip())
        else:
            non_questions.append(clause.strip())

    # If no questions were detected via clause starts, try to find an
    # inline auxiliary-started yes/no question anywhere in the text
    # Example: "It rains and if it rains, the ground is wet, is the ground wet?"
    if not questions:
        # Anchor the search to the final question mark to avoid matching
        # earlier auxiliary words inside premises (pick the clause that
        # actually ends the input with a question).
        cleaned = raw_input.strip()
        pattern = re.compile(r"\b(" + "|".join(sorted(AUXILIARIES, key=lambda x: -len(x))) + r")\b[^?]*\?$",
                             flags=re.IGNORECASE | re.DOTALL)
        m = pattern.search(cleaned)
        if m:
            q = cleaned[m.start():m.end()].strip()
            # remove the found question substring from the non_questions text
            remaining = (cleaned[:m.start()] + cleaned[m.end():]).strip()

            # re-split remaining text into non-question clauses, include commas
            remaining_clauses = [c.strip() for c in re.split(r"[,?.!]+", remaining) if c.strip()]

            questions = [q]
            non_questions = remaining_clauses

    # Fallback: punctuation-free trailing question heuristic
    # If still no question found and the input contains no terminal '?' and no sentence punctuation,
    # attempt a conservative detection of a trailing auxiliary-led clause as question.
    if not questions:
        cleaned = raw_input.strip()
        # Only attempt this when there is no obvious sentence-ending punctuation
        if not re.search(r"[.?!]", cleaned):
            aux_pattern = r"\b(" + "|".join(sorted(AUXILIARIES, key=lambda x: -len(x))) + r")\b\s+"
            # Look near the end for an auxiliary followed by a short clause
            m2 = re.search(aux_pattern + r"(.{1,60})$", cleaned, flags=re.IGNORECASE)
            if m2:
                candidate = cleaned[m2.start():].strip()
                # Heuristic: require at least two words in candidate (aux + subject/predicate)
                if len(candidate.split()) >= 2:
                    remaining = cleaned[:m2.start()].strip()
                    remaining_clauses = [c.strip() for c in re.split(r"[,;]+", remaining) if c.strip()]
                    # Conservative: only accept if there is some remaining premise text
                    if remaining_clauses:
                        questions = [candidate]
                        non_questions = remaining_clauses

    return questions, non_questions


def segment_premises_with_llm(candidate_premise_text: str) -> Dict[str, Any]:
    user_prompt = f"""Candidate premise text:
{candidate_premise_text}
"""
    return call_llm_json(PREMISE_SEGMENTATION_PROMPT, user_prompt)


def normalize_premise_with_llm(sentence: str) -> Dict[str, Any]:
    user_prompt = f"""Premise sentence:
{sentence}
"""
    return call_llm_json(PREMISE_NORMALIZATION_PROMPT, user_prompt)


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
            predicate = " ".join(rest_words[not_index + 1:])
            return [f"not {subject} {aux} {predicate}"]

        if len(rest_words) >= 3 and rest_words[1].lower() in {"a", "an", "the"}:
            subject = rest_words[0]
            predicate = " ".join(rest_words[1:])
        else:
            subject = " ".join(rest_words[:-1])
            predicate = rest_words[-1]

        return [f"{subject} {aux} {predicate}"]

    if aux in {"has", "have", "had", "will", "would", "can", "could", "shall", "should", "may", "might", "must"}:
        return [" ".join(rest_words[:1] + [words[0].lower()] + rest_words[1:])]

    if aux in {"do", "does"}:
        if len(rest_words) < 2:
            return [" ".join(rest_words)]

        subject = rest_words[0]
        verb = rest_words[1]
        after = rest_words[2:]

        if aux == "does":
            proposition_without_do = " ".join([subject, verb_to_third_person(verb)] + after)
        else:
            proposition_without_do = " ".join([subject, verb] + after)

        proposition_with_do = " ".join([subject, aux, verb] + after)

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


def analyze_atom_relations_with_llm(atom_table: List[Dict[str, str]]) -> Dict[str, Any]:
    user_prompt = "Atom table:\n" + json.dumps(atom_table, indent=2)
    try:
        return call_llm_json(ATOM_RELATION_PROMPT, user_prompt)
    except Exception:
        # Fallback: no LLM available or LLM error — assume no synonyms/opposites.
        return {"success": True, "groups": [], "opposites": []}

def are_tense_variants_not_opposites(text1: str, text2: str) -> bool:
    a = text1.lower().strip().rstrip(".")
    b = text2.lower().strip().rstrip(".")

    tense_variant_pairs = {
        ("it rains", "it rained"),
        ("it is raining", "it rained"),
        ("it rains", "it was raining"),
    }

    return (a, b) in tense_variant_pairs or (b, a) in tense_variant_pairs

def state_result_equivalent(text1: str, text2: str) -> bool:
    a = text1.lower().strip().rstrip(".")
    b = text2.lower().strip().rstrip(".")

    def parse_gets_or_becomes_state(text: str):
        # Examples:
        # "the ground gets wet" -> ("the ground", "wet")
        # "the door becomes open" -> ("the door", "open")
        for marker in [" gets ", " becomes "]:
            if marker in text:
                subject, state = text.split(marker, 1)
                return subject.strip(), state.strip()
        return None

    def parse_is_state(text: str):
        # Example:
        # "the ground is wet" -> ("the ground", "wet")
        if " is " in text:
            subject, state = text.split(" is ", 1)
            return subject.strip(), state.strip()
        return None

    parsed_a_event = parse_gets_or_becomes_state(a)
    parsed_b_state = parse_is_state(b)

    if parsed_a_event and parsed_b_state:
        return parsed_a_event == parsed_b_state

    parsed_b_event = parse_gets_or_becomes_state(b)
    parsed_a_state = parse_is_state(a)

    if parsed_b_event and parsed_a_state:
        return parsed_b_event == parsed_a_state

    return False

def is_negated_atom(text: str) -> bool:
    return text.lower().strip().startswith("not ")

def build_atom_mapping(
    atom_table: List[Dict[str, str]],
    relation_result: Dict[str, Any],
) -> Dict[str, str]:
    mapping = {atom["id"]: atom["text"] for atom in atom_table}
    id_to_text = {atom["id"]: atom["text"] for atom in atom_table}

    for group in relation_result.get("groups", []):
        canonical = group["canonical"]
        members = group.get("members", [])

        # Guard: do not allow positive and negated atoms in the same synonym group.
        member_texts = [mapping.get(member, "") for member in members]

        has_negated = any(is_negated_atom(text) for text in member_texts)
        has_positive = any(not is_negated_atom(text) for text in member_texts)

        if has_negated and has_positive:
            continue

        for member in members:
            mapping[member] = canonical

    # Deterministic repair for general state-result equivalence.
    # Example: "the ground gets wet" <-> "the ground is wet"
    premise_atoms = [atom for atom in atom_table if atom["source"].startswith("P")]
    question_atoms = [atom for atom in atom_table if atom["source"] == "question"]

    for p_atom in premise_atoms:
        for q_atom in question_atoms:
            if state_result_equivalent(p_atom["text"], q_atom["text"]):
                mapping[q_atom["id"]] = mapping.get(p_atom["id"], p_atom["text"])
                
    for opposite in relation_result.get("opposites", []):
        positive = opposite["positive"]

        positive_members = opposite.get("positive_members", [])
        negative_members = opposite.get("negative_members", [])

        # Guard 1: opposite relation must have both sides grounded in actual atoms.
        if not positive_members or not negative_members:
            continue

        # Guard 2: tense/time variants are not opposites.
        invalid_opposite = False
        for p_member in positive_members:
            for n_member in negative_members:
                if are_tense_variants_not_opposites(
                    id_to_text.get(p_member, ""),
                    id_to_text.get(n_member, ""),
                ):
                    invalid_opposite = True

        if invalid_opposite:
            continue

        for member in positive_members:
            mapping[member] = positive

        for member in negative_members:
            mapping[member] = f"not {positive}"

    return mapping


def rebuild_premise(pattern: str, atoms: List[str]) -> str:
    if pattern == "conditional":
        return f"If {atoms[0]}, then {atoms[1]}."

    if pattern == "negation":
        return f"Not {atoms[0]}."

    if pattern == "conjunction":
        return f"{atoms[0]} and {atoms[1]}."

    if pattern == "disjunction":
        return f"{atoms[0]} or {atoms[1]}."

    return f"{atoms[0]}."


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
                rest = inner[idx + len(marker):]
                aux = marker.strip()
                return f"{aux.capitalize()} {normalize_question_subject_case(subject)} not {rest}?"

        return f"Is it not true that {inner}?"

    # be-verb forms
    for marker in [" is not ", " are not ", " was not ", " were not "]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker):]
            aux = marker.strip().split()[0]
            return f"{aux.capitalize()} {subject} not {rest}?"

    for marker in [" is ", " are ", " was ", " were "]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker):]
            aux = marker.strip()
            return f"{aux.capitalize()} {normalize_question_subject_case(subject)} {rest}?"

    # modal / have forms
    for marker in [" has ", " have ", " had ", " will ", " can ", " could ", " should ", " would ", " must "]:
        if marker in lower:
            idx = lower.index(marker)
            subject = p[:idx]
            rest = p[idx + len(marker):]
            aux = marker.strip()
            return f"{aux.capitalize()} {subject} {rest}?"

    words = p.split()

    # find first likely third-person verb ending in s after at least one subject word
    for i in range(1, len(words)):
        word = words[i]
        lw = word.lower()

        if lw.endswith("s") and lw not in {"is", "was", "has"}:
            subject = " ".join(words[:i])
            verb = base_verb_from_third_person(word)
            rest = " ".join(words[i + 1:])
            return f"Does {normalize_question_subject_case(subject)} {verb}{(' ' + rest) if rest else ''}?"

    return f"Does {p}?"

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
        "If", "Then", "Not", "Either", "The", "A", "An", "It", "He", "She", "They"
    }

    possible_names = [name for name in names if name not in non_names]
    unique_names = set(possible_names)

    has_pronoun = bool(re.search(r"\b(he|she|they|him|her|them)\b", joined, re.IGNORECASE))

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
            rest = s[idx + len(marker):]
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

def normalize_raw_prompt(raw_input: str) -> Dict[str, Any]:
    if not raw_input or not raw_input.strip():
        return make_error("Empty input")
    # Conservative policy: if the entire input contains no sentence-ending
    # punctuation, do not attempt aggressive segmentation. Return a clear
    # error so callers can decide how to proceed.
    if not re.search(r"[.?!]", raw_input):
        return make_error("Could not safely detect exactly one yes/no question from punctuation-free input")
    questions, non_questions = detect_yes_no_questions(raw_input)

    if len(questions) == 0:
        # If the input contains no sentence-ending punctuation, provide
        # a clearer, conservative error message indicating inability to
        # safely detect a single yes/no question from punctuation-free input.
        if not re.search(r"[.?!]", raw_input):
            return make_error("Could not safely detect exactly one yes/no question from punctuation-free input")
        return make_error("No yes/no question detected")

    if len(questions) > 1:
        return make_error("More than one question detected")

    raw_question = questions[0]
    candidate_premise_text = "\n".join(non_questions).strip()

    if not candidate_premise_text:
        return make_error("No candidate premises found")

    # If deterministic clause splitting already found candidate premises,
    # keep them exactly as written. Do not let the LLM remove words like "If".
    if non_questions:
        raw_premises = non_questions
    else:
        segmentation = segment_premises_with_llm(candidate_premise_text)

        if not segmentation.get("success"):
            return make_error(segmentation.get("error", "Could not separate candidate premises"))

        raw_premises = segmentation.get("premises", [])

    if not raw_premises:
        return make_error("Could not separate candidate premises into proper English sentences")

    if contains_ambiguous_pronoun(raw_premises):
        return make_error("Ambiguous pronoun reference")

    normalized_premises = []

    for premise in raw_premises:
        if is_irrelevant_or_noisy_text(premise):
            return make_error("Irrelevant or noisy text")
        if is_quantified_or_general_statement(premise):
            return make_error("Quantified/general/category-wide statement")
        if has_compound_subject(premise):
            return make_error("Unsupported statement pattern")
        deterministic_conditional = deterministic_conditional_rewrite(premise)

        if deterministic_conditional is not None:
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
            return make_error(normalized.get("error", "Unsupported statement pattern"))

        normalized_sentence = normalized["normalized_sentence"].strip().rstrip(".") + "."
        normalized_premises.append(normalized_sentence)

    atom_table, metadata = create_atom_table(normalized_premises, raw_question)

    relation_result = analyze_atom_relations_with_llm(atom_table)

    if not relation_result.get("success"):
        return make_error(relation_result.get("error", "Ambiguous atom relation"))

    atom_mapping = build_atom_mapping(atom_table, relation_result)

    final_premises = []

    for structure in metadata["premise_structures"]:
        atoms = [atom_mapping[atom_id] for atom_id in structure["atom_ids"]]
        final_premises.append(rebuild_premise(structure["pattern"], atoms))

    question_candidates = metadata["question_atom_ids"]

    if not question_candidates:
        return make_error("Could not extract target atom from question")

    # Prefer mapped canonical form of first question candidate.
    # If multiple do-question candidates exist, relation mapping should make them converge.
    canonical_question_atom = atom_mapping[question_candidates[0]]
    final_question = proposition_to_question(canonical_question_atom)

    normalized_output = "Premises:\n"
    for i, premise in enumerate(final_premises, start=1):
        normalized_output += f"{i}. {premise}\n"

    normalized_output += f"\nQuestion:\n{final_question}"

    return {
        "success": True,
        "normalized_input": normalized_output,
        "error": None,
        "debug": {
            "questions": questions,
            "raw_premises": raw_premises,
            "normalized_premises_before_atom_unification": normalized_premises,
            "atom_table": atom_table,
            "relation_result": relation_result,
            "atom_mapping": atom_mapping,
        },
    }