import json
from typing import Any, Dict, List

from prompts import ATOM_RELATION_PROMPT
from normalizer.llm_utils import call_llm_json


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
