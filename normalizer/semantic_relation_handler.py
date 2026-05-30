import re
from typing import Any, Dict, List

from normalizer.llm_utils import call_llm_json
from prompts.semantic_relation_prompt import SEMANTIC_RELATION_PROMPT


ERROR_SEMANTIC_RELATION = "Ambiguous semantic relationship detected"

VALID_RELATIONS = {
    "SYNONYM",
    "ANTONYM",
    "NO_RELATION",
    "AMBIGUOUS",
}


def _make_failure(
    ambiguous_pair: Dict[str, Any] | None = None,
    comparisons: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "semantic_relation_success": False,
        "atom_table": [],
        "canonical_atom_table": [],
        "atom_id_map": {},
        "semantic_pairs": [],
        "synonym_pairs": [],
        "antonym_pairs": [],
        "ambiguous_pair": ambiguous_pair,
        "comparisons": comparisons or [],
        "semantic_unified_premises": [],
        "semantic_unified_question": None,
        "semantic_unified_prompt": None,
        "errors": [ERROR_SEMANTIC_RELATION],
        "error": ERROR_SEMANTIC_RELATION,
    }


def _make_success(
    atom_table: List[Dict[str, Any]],
    canonical_atom_table: List[Dict[str, Any]],
    atom_id_map: Dict[str, str],
    semantic_pairs: List[Dict[str, Any]],
    synonym_pairs: List[Dict[str, Any]],
    antonym_pairs: List[Dict[str, Any]],
    comparisons: List[Dict[str, Any]],
    semantic_unified_premises: List[str],
    semantic_unified_question: str,
    semantic_unified_prompt: str,
) -> Dict[str, Any]:
    return {
        "success": True,
        "semantic_relation_success": True,
        "atom_table": atom_table,
        "canonical_atom_table": canonical_atom_table,
        "atom_id_map": atom_id_map,
        "semantic_pairs": semantic_pairs,
        "synonym_pairs": synonym_pairs,
        "antonym_pairs": antonym_pairs,
        "ambiguous_pair": None,
        "comparisons": comparisons,
        "semantic_unified_premises": semantic_unified_premises,
        "semantic_unified_question": semantic_unified_question,
        "semantic_unified_prompt": semantic_unified_prompt,
        "errors": [],
        "error": None,
    }


def _normalize_atom_text(atom_text: str) -> str:
    cleaned = " ".join(str(atom_text).strip().lower().rstrip(".").split())
    return f"{cleaned}."


def _words(atom_text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", atom_text.lower())


def _copy_atom_table(atom_table: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    copied = []

    for atom in atom_table:
        copied.append(
            {
                "atom_id": str(atom["atom_id"]),
                "atom_text": _normalize_atom_text(atom["atom_text"]),
            }
        )

    return copied


def _find_atom(atom_table: List[Dict[str, Any]], atom_id: str) -> Dict[str, Any]:
    for atom in atom_table:
        if atom["atom_id"] == atom_id:
            return atom

    raise KeyError(f"Atom ID not found: {atom_id}")


def _extract_simple_subject_from_atom(atom_text: str) -> str | None:
    words = _words(atom_text)

    if len(words) < 2:
        return None

    if words[0] in {"the", "a", "an"}:
        if len(words) >= 2:
            return " ".join(words[:2])
        return None

    return words[0]


def _subjects_are_clearly_different(atom_a_text: str, atom_b_text: str) -> bool:
    subject_a = _extract_simple_subject_from_atom(atom_a_text)
    subject_b = _extract_simple_subject_from_atom(atom_b_text)

    if subject_a is None or subject_b is None:
        return False

    return subject_a != subject_b


def _same_subject_words(a_words: List[str], b_words: List[str]) -> bool:
    if not a_words or not b_words:
        return False

    return a_words[0] == b_words[0]


def _is_present_continuous_form(words: List[str]) -> bool:
    return (
        len(words) >= 3
        and words[1] in {"is", "are", "am"}
        and words[2].endswith("ing")
    )


def _is_simple_present_like_form(words: List[str]) -> bool:
    return (
        len(words) >= 2
        and words[1] not in {
            "is",
            "are",
            "am",
            "was",
            "were",
            "will",
            "did",
            "do",
            "does",
        }
    )


def _deterministic_pair_relation(
    atom_a_text: str,
    atom_b_text: str,
) -> Dict[str, str] | None:
    a_words = _words(atom_a_text)
    b_words = _words(atom_b_text)

    if a_words == b_words:
        return {
            "relation": "SYNONYM",
            "reason": "The atoms are textually identical after normalization.",
        }

    if _is_state_vs_process_pair(atom_a_text, atom_b_text):
        return {
            "relation": "AMBIGUOUS",
            "reason": "State and change/process predicates are not safely equivalent.",
        }

    lexical_relation = _predicate_relation_from_lexicon(
        atom_a_text=atom_a_text,
        atom_b_text=atom_b_text,
    )

    if lexical_relation is not None:
        return lexical_relation

    if _same_subject_words(a_words, b_words):
        a_continuous = _is_present_continuous_form(a_words)
        b_continuous = _is_present_continuous_form(b_words)

        a_simple_present = _is_simple_present_like_form(a_words)
        b_simple_present = _is_simple_present_like_form(b_words)

        if (a_simple_present and b_continuous) or (a_continuous and b_simple_present):
            return {
                "relation": "AMBIGUOUS",
                "reason": "Simple present and present continuous can differ in truth condition.",
            }

    # Do-support equivalent:
    # ahmed passes / ahmed does pass
    if len(a_words) >= 2 and len(b_words) >= 3:
        if b_words[1] in {"do", "does"}:
            subject_same = a_words[0] == b_words[0]
            main_same_or_s_form = (
                a_words[1] == b_words[2]
                or a_words[1] == b_words[2] + "s"
                or a_words[1] == b_words[2] + "es"
            )

            if subject_same and main_same_or_s_form and a_words[2:] == b_words[3:]:
                return {
                    "relation": "SYNONYM",
                    "reason": "The atoms differ only by do-support.",
                }

        if a_words[1] in {"do", "does"}:
            subject_same = a_words[0] == b_words[0]
            main_same_or_s_form = (
                b_words[1] == a_words[2]
                or b_words[1] == a_words[2] + "s"
                or b_words[1] == a_words[2] + "es"
            )

            if subject_same and main_same_or_s_form and a_words[3:] == b_words[2:]:
                return {
                    "relation": "SYNONYM",
                    "reason": "The atoms differ only by do-support.",
                }

    # Present/general vs past do-support.
    if len(a_words) >= 2 and len(b_words) >= 3:
        if b_words[1] == "did" and a_words[0] == b_words[0]:
            return {
                "relation": "NO_RELATION",
                "reason": "Present/general and past do-support have different truth conditions.",
            }

        if a_words[1] == "did" and a_words[0] == b_words[0]:
            return {
                "relation": "NO_RELATION",
                "reason": "Present/general and past do-support have different truth conditions.",
            }

    return None


def _build_user_prompt(
    half_normalized_prompt: str,
    atom_a_text: str,
    atom_b_text: str,
) -> str:
    atom_a_parts = _extract_subject_and_predicate(atom_a_text)
    atom_b_parts = _extract_subject_and_predicate(atom_b_text)

    if atom_a_parts is None:
        atom_a_subject = "UNKNOWN"
        atom_a_predicate = atom_a_text
    else:
        atom_a_subject, atom_a_predicate = atom_a_parts

    if atom_b_parts is None:
        atom_b_subject = "UNKNOWN"
        atom_b_predicate = atom_b_text
    else:
        atom_b_subject, atom_b_predicate = atom_b_parts

    return f"""
Half-normalized prompt:
{half_normalized_prompt}

Atom A:
{atom_a_text}

Atom A subject:
{atom_a_subject}

Atom A predicate/property/action:
{atom_a_predicate}

Atom B:
{atom_b_text}

Atom B subject:
{atom_b_subject}

Atom B predicate/property/action:
{atom_b_predicate}

Classify the semantic relation between Atom A and Atom B.

Important:
Base the relation mainly on the predicate/property/action meanings.
Different subjects do not automatically mean NO_RELATION.
If the subjects differ but the predicates are synonyms, return SYNONYM.
If the subjects differ but the predicates are direct opposites, return ANTONYM.
If the predicates are unrelated, return NO_RELATION.

Return ONLY valid JSON in this exact format:
{{
  "relation": "SYNONYM" | "ANTONYM" | "NO_RELATION" | "AMBIGUOUS",
  "reason": "<short reason>"
}}
""".strip()


def _validate_llm_relation(raw_result: Dict[str, Any]) -> Dict[str, str]:
    if not isinstance(raw_result, dict):
        return {
            "relation": "AMBIGUOUS",
            "reason": "LLM result was not a JSON object.",
        }

    relation = str(raw_result.get("relation", "")).strip().upper()
    reason = str(raw_result.get("reason", "")).strip()

    if relation not in VALID_RELATIONS:
        return {
            "relation": "AMBIGUOUS",
            "reason": "LLM relation was not one of the allowed labels.",
        }

    if not reason:
        reason = "No reason provided."

    return {
        "relation": relation,
        "reason": reason,
    }


def _repair_llm_relation(parsed: Dict[str, str]) -> Dict[str, str]:
    relation = parsed["relation"]
    reason = parsed["reason"].lower()

        # Preserve formal-risk ambiguity.
    # State vs process/change is intentionally AMBIGUOUS, not NO_RELATION.
    if relation == "AMBIGUOUS":
        ambiguity_preserve_signals = [
            "state and change/process",
            "state vs change/process",
            "state vs process",
            "change/process",
            "process predicates",
        ]

        if any(signal in reason for signal in ambiguity_preserve_signals):
            return parsed
            
    if relation == "AMBIGUOUS":
        no_relation_reason_signals = [
            "not interchangeable",
            "not clearly interchangeable",
            "not safely interchangeable",
            "not equivalent",
            "not clearly equivalent",
            "not safely equivalent",
            "different meaning",
            "different meanings",
            "different predicate",
            "different predicates",
            "different property",
            "different properties",
            "different proposition",
            "different propositions",
            "different positive description",
            "different positive descriptions",
            "different tense/aspect",
            "clearly different",
            "related but not",
            "unrelated",
            "unrelated action",
            "unrelated actions",
            "unrelated predicate",
            "unrelated predicates",
        ]

        if any(signal in reason for signal in no_relation_reason_signals):
            return {
                "relation": "NO_RELATION",
                "reason": parsed["reason"],
            }

    # --------------------------------------------------
    # Repair over-permissive SYNONYM decisions.
    # "Same positive description" / "both positive" is not enough
    # for synonymy. Synonymy requires same property, not just
    # same sentiment.
    # --------------------------------------------------
    if relation == "SYNONYM":
        weak_synonym_reason_signals = [
            "same positive description",
            "both positive",
            "positive description",
            "same sentiment",
            "similar sentiment",
            "same evaluation",
            "similar evaluation",
            "equivalent predicate meaning",
            "equivalent predicate",
            "equivalent property",
        ]

        if any(signal in reason for signal in weak_synonym_reason_signals):
            return {
                "relation": "NO_RELATION",
                "reason": parsed["reason"],
            }

    return parsed


def _build_canonical_atom_table(
    unified_atom_table: List[Dict[str, Any]],
    atom_id_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    canonical_ids = []

    for atom in unified_atom_table:
        canonical_id = atom_id_map[atom["atom_id"]]

        if canonical_id not in canonical_ids:
            canonical_ids.append(canonical_id)

    canonical_table = []

    for canonical_id in canonical_ids:
        canonical_atom = _find_atom(unified_atom_table, canonical_id)

        canonical_table.append(
            {
                "atom_id": canonical_atom["atom_id"],
                "atom_text": canonical_atom["atom_text"],
            }
        )

    return canonical_table


def _canonical_atom_text_by_id(
    canonical_atom_table: List[Dict[str, Any]],
) -> Dict[str, str]:
    return {
        atom["atom_id"]: atom["atom_text"]
        for atom in canonical_atom_table
    }


def _original_to_canonical_text_map(
    original_atom_table: List[Dict[str, Any]],
    atom_id_map: Dict[str, str],
    canonical_atom_table: List[Dict[str, Any]],
) -> Dict[str, str]:
    canonical_text_by_id = _canonical_atom_text_by_id(canonical_atom_table)
    text_map = {}

    for atom in original_atom_table:
        atom_id = atom["atom_id"]
        original_text = _normalize_atom_text(atom["atom_text"])
        canonical_id = atom_id_map.get(atom_id, atom_id)
        canonical_text = canonical_text_by_id.get(canonical_id, original_text)

        text_map[original_text] = canonical_text

    return text_map


def _sentence_to_question(sentence: str) -> str:
    words = _normalize_atom_text(sentence).rstrip(".").split()

    if len(words) < 2:
        return _normalize_atom_text(sentence).rstrip(".") + "?"

    auxiliaries = {
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

    determiners = {"the", "a", "an"}

    if words[0] in determiners and len(words) >= 3:
        subject_words = words[:2]
        predicate_words = words[2:]
    else:
        subject_words = words[:1]
        predicate_words = words[1:]

    if not predicate_words:
        return " ".join(words) + "?"

    if predicate_words[0] in auxiliaries:
        aux = predicate_words[0]
        rest = predicate_words[1:]
        return " ".join([aux] + subject_words + rest) + "?"

    first_predicate = predicate_words[0]
    remaining_predicate = predicate_words[1:]

    if first_predicate.endswith("ies") and len(first_predicate) > 3:
        base_verb = first_predicate[:-3] + "y"
    elif first_predicate.endswith("es") and len(first_predicate) > 2:
        base_verb = first_predicate[:-2]
    elif first_predicate.endswith("s") and len(first_predicate) > 1:
        base_verb = first_predicate[:-1]
    else:
        base_verb = first_predicate

    return " ".join(["does"] + subject_words + [base_verb] + remaining_predicate) + "?"


def _build_normalized_prompt_text(
    premises: List[str],
    question: str,
) -> str:
    lines = ["Premises:"]

    for index, premise in enumerate(premises, start=1):
        lines.append(f"{index}. {premise}")

    lines.append("")
    lines.append("Question:")
    lines.append(question)

    return "\n".join(lines)


def _apply_semantic_unification_to_prompt(
    premises: List[str],
    question: str,
    target_atoms: List[Dict[str, Any]],
    original_atom_table: List[Dict[str, Any]],
    atom_id_map: Dict[str, str],
    canonical_atom_table: List[Dict[str, Any]],
) -> tuple[List[str], str, str]:
    text_map = _original_to_canonical_text_map(
        original_atom_table=original_atom_table,
        atom_id_map=atom_id_map,
        canonical_atom_table=canonical_atom_table,
    )

    semantic_unified_premises = []

    for premise in premises:
        updated_premise = _normalize_atom_text(premise)

        for original_text, canonical_text in text_map.items():
            if original_text == canonical_text:
                continue

            updated_premise = updated_premise.replace(
                original_text.rstrip("."),
                canonical_text.rstrip("."),
            )

        semantic_unified_premises.append(updated_premise)

    semantic_unified_question = question

    for target in target_atoms or []:
        target_id = target["atom_id"]
        original_target_text = _normalize_atom_text(target["atom_text"])
        canonical_id = atom_id_map.get(target_id, target_id)

        for canonical_atom in canonical_atom_table:
            if canonical_atom["atom_id"] == canonical_id:
                canonical_atom_text = _normalize_atom_text(canonical_atom["atom_text"])

                # If the target atom did not actually change, leave the question as is.
                if canonical_atom_text == original_target_text:
                    break

                if canonical_atom_text.startswith("not "):
                    semantic_unified_question = _negated_sentence_to_question(
                        canonical_atom_text
                    )
                else:
                    semantic_unified_question = _sentence_to_question(
                        canonical_atom_text
                    )

                break

    semantic_unified_prompt = _build_normalized_prompt_text(
        premises=semantic_unified_premises,
        question=semantic_unified_question,
    )

    return (
        semantic_unified_premises,
        semantic_unified_question,
        semantic_unified_prompt,
    )


def handle_semantic_relations(
    atom_table: List[Dict[str, Any]],
    half_normalized_prompt: str,
    premises: List[str] | None = None,
    question: str | None = None,
    target_atoms: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Normalizer Component N9: Semantic Relation Handler.

    This component replaces the old separate synonym and antonym unifiers.

    Relations:
    - SYNONYM: later atom becomes earlier atom.
    - ANTONYM: later atom becomes "not <earlier atom>".
    - NO_RELATION: atoms remain separate.
    - AMBIGUOUS: fail immediately.
    """

    if not isinstance(atom_table, list) or not atom_table:
        return _make_failure()

    original_atom_table = _copy_atom_table(atom_table)
    unified_atom_table = _copy_atom_table(atom_table)

    atom_id_map = {
        atom["atom_id"]: atom["atom_id"]
        for atom in unified_atom_table
    }

    comparisons = []
    semantic_pairs = []
    synonym_pairs = []
    antonym_pairs = []

    total_atoms = len(unified_atom_table)

    for i in range(total_atoms):
        atom_i = unified_atom_table[i]

        # If atom_i was already unified into an earlier atom,
        # it should not act as the base for later comparisons.
        if atom_id_map[atom_i["atom_id"]] != atom_i["atom_id"]:
            continue

        # Negated atoms are normalized outputs, not base predicates for new comparisons.
        if _normalize_atom_text(atom_i["atom_text"]).startswith("not "):
            continue

        canonical_i_id = atom_id_map[atom_i["atom_id"]]
        canonical_i = _find_atom(unified_atom_table, canonical_i_id)

        for j in range(i + 1, total_atoms):
            atom_j = unified_atom_table[j]

            # If atom_j was already unified into an earlier canonical atom,
            # do not compare/remap it again.
            if atom_id_map[atom_j["atom_id"]] != atom_j["atom_id"]:
                continue

            # If atom_j was already rewritten as a negated atom, do not remap it again.
            if _normalize_atom_text(atom_j["atom_text"]).startswith("not "):
                continue

            canonical_j_id = atom_id_map[atom_j["atom_id"]]
            canonical_j = _find_atom(unified_atom_table, canonical_j_id)

            if canonical_i_id == canonical_j_id:
                continue

            atom_a_text = canonical_i["atom_text"]
            atom_b_text = canonical_j["atom_text"]

            deterministic_relation = _deterministic_pair_relation(
                atom_a_text=atom_a_text,
                atom_b_text=atom_b_text,
            )

            if deterministic_relation is not None:
                parsed = deterministic_relation
            else:
                user_prompt = _build_user_prompt(
                    half_normalized_prompt=half_normalized_prompt,
                    atom_a_text=atom_a_text,
                    atom_b_text=atom_b_text,
                )

                raw_llm_result = call_llm_json(
                    system_prompt=SEMANTIC_RELATION_PROMPT,
                    user_prompt=user_prompt,
                )

                parsed = _validate_llm_relation(raw_llm_result)

            parsed = _repair_llm_relation(parsed)

            relation = parsed["relation"]
            reason = parsed["reason"]

            comparison = {
                "atom_a_id": canonical_i_id,
                "atom_a_text": atom_a_text,
                "atom_b_id": canonical_j_id,
                "atom_b_text": atom_b_text,
                "relation": relation,
                "reason": reason,
            }

            comparisons.append(comparison)

            if relation == "AMBIGUOUS":
                return _make_failure(
                    ambiguous_pair=comparison,
                    comparisons=comparisons,
                )

            if relation == "NO_RELATION":
                continue

            if relation == "SYNONYM":
                same_subject = _subjects_are_same(atom_a_text, atom_b_text)

                if same_subject:
                    rewritten_atom_text = atom_a_text
                    atom_id_map[atom_j["atom_id"]] = canonical_i_id
                else:
                    rewritten_atom_text = _build_synonym_rewritten_atom(
                        base_atom_text=atom_a_text,
                        target_atom_text=atom_b_text,
                    )

                    # Different-subject synonym predicates are rewritten,
                    # but they remain distinct atoms because they are different propositions.
                    atom_id_map[atom_j["atom_id"]] = atom_j["atom_id"]

                atom_j["atom_text"] = rewritten_atom_text

                pair = {
                    "relation": "SYNONYM",
                    "kept_atom_id": canonical_i_id,
                    "kept_atom_text": atom_a_text,
                    "replaced_atom_id": atom_j["atom_id"],
                    "original_replaced_atom_text": atom_b_text,
                    "new_replaced_atom_text": rewritten_atom_text,
                    "same_subject": same_subject,
                }

                semantic_pairs.append(pair)
                synonym_pairs.append(pair)
                continue

            if relation == "ANTONYM":
                negated_atom_text = _build_antonym_rewritten_atom(
                    base_atom_text=atom_a_text,
                    target_atom_text=atom_b_text,
                )

                # Antonym rewrite remains a distinct atom.
                atom_id_map[atom_j["atom_id"]] = atom_j["atom_id"]
                atom_j["atom_text"] = negated_atom_text

                pair = {
                    "relation": "ANTONYM",
                    "base_atom_id": canonical_i_id,
                    "base_atom_text": atom_a_text,
                    "negated_atom_id": atom_j["atom_id"],
                    "original_negated_atom_text": atom_b_text,
                    "new_negated_atom_text": negated_atom_text,
                }

                semantic_pairs.append(pair)
                antonym_pairs.append(pair)
                continue
    canonical_atom_table = _build_canonical_atom_table(
        unified_atom_table=unified_atom_table,
        atom_id_map=atom_id_map,
    )

    if premises is not None and question is not None:
        (
            semantic_unified_premises,
            semantic_unified_question,
            semantic_unified_prompt,
        ) = _apply_semantic_unification_to_prompt(
            premises=premises,
            question=question,
            target_atoms=target_atoms or [],
            original_atom_table=original_atom_table,
            atom_id_map=atom_id_map,
            canonical_atom_table=canonical_atom_table,
        )
    else:
        semantic_unified_premises = premises or []
        semantic_unified_question = question or ""
        semantic_unified_prompt = half_normalized_prompt

    return _make_success(
        atom_table=unified_atom_table,
        canonical_atom_table=canonical_atom_table,
        atom_id_map=atom_id_map,
        semantic_pairs=semantic_pairs,
        synonym_pairs=synonym_pairs,
        antonym_pairs=antonym_pairs,
        comparisons=comparisons,
        semantic_unified_premises=semantic_unified_premises,
        semantic_unified_question=semantic_unified_question,
        semantic_unified_prompt=semantic_unified_prompt,
    )
def _negated_sentence_to_question(sentence: str) -> str:
    """
    Converts a negated canonical atom into a yes/no question.

    Example:
    not the door is open.
    -> is the door not open?

    not ahmed is happy.
    -> is ahmed not happy?
    """

    clean_sentence = _normalize_atom_text(sentence)

    if not clean_sentence.startswith("not "):
        return _sentence_to_question(clean_sentence)

    positive_sentence = clean_sentence[4:]
    positive_words = _normalize_atom_text(positive_sentence).rstrip(".").split()

    if len(positive_words) < 2:
        return "is not " + " ".join(positive_words) + "?"

    auxiliaries = {
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

    determiners = {"the", "a", "an"}

    if positive_words[0] in determiners and len(positive_words) >= 3:
        subject_words = positive_words[:2]
        predicate_words = positive_words[2:]
    else:
        subject_words = positive_words[:1]
        predicate_words = positive_words[1:]

    if not predicate_words:
        return "is " + " ".join(subject_words) + " not?"

    if predicate_words[0] in auxiliaries:
        aux = predicate_words[0]
        rest = predicate_words[1:]
        return " ".join([aux] + subject_words + ["not"] + rest) + "?"

    # Fallback for simple present action atoms:
    # not ahmed studies. -> does ahmed not study?
    first_predicate = predicate_words[0]
    remaining_predicate = predicate_words[1:]

    if first_predicate.endswith("ies") and len(first_predicate) > 3:
        base_verb = first_predicate[:-3] + "y"
    elif first_predicate.endswith("es") and len(first_predicate) > 2:
        base_verb = first_predicate[:-2]
    elif first_predicate.endswith("s") and len(first_predicate) > 1:
        base_verb = first_predicate[:-1]
    else:
        base_verb = first_predicate

    return " ".join(["does"] + subject_words + ["not", base_verb] + remaining_predicate) + "?"

def _extract_subject_and_predicate(atom_text: str) -> tuple[str, str] | None:
    """
    Splits a normalized atom into subject and predicate.

    Examples:
    ahmed is happy. -> ("ahmed", "is happy")
    the door is open. -> ("the door", "is open")
    """

    words = _normalize_atom_text(atom_text).rstrip(".").split()

    if len(words) < 2:
        return None

    if words[0] in {"the", "a", "an"} and len(words) >= 3:
        subject = " ".join(words[:2])
        predicate = " ".join(words[2:])
    else:
        subject = words[0]
        predicate = " ".join(words[1:])

    return subject, predicate


def _subjects_are_same(atom_a_text: str, atom_b_text: str) -> bool:
    atom_a_parts = _extract_subject_and_predicate(atom_a_text)
    atom_b_parts = _extract_subject_and_predicate(atom_b_text)

    if atom_a_parts is None or atom_b_parts is None:
        return False

    subject_a, _ = atom_a_parts
    subject_b, _ = atom_b_parts

    return subject_a == subject_b


def _build_synonym_rewritten_atom(
    base_atom_text: str,
    target_atom_text: str,
) -> str:
    """
    Rewrites target atom using base atom's predicate while preserving
    target atom's subject.

    Examples:
    base:   ahmed is happy.
    target: mohamed is joyful.
    output: mohamed is happy.

    base:   the machine starts.
    target: the device begins.
    output: the device starts.
    """

    base_parts = _extract_subject_and_predicate(base_atom_text)
    target_parts = _extract_subject_and_predicate(target_atom_text)

    if base_parts is None or target_parts is None:
        return _normalize_atom_text(base_atom_text)

    _, base_predicate = base_parts
    target_subject, _ = target_parts

    return _normalize_atom_text(f"{target_subject} {base_predicate}")


def _build_antonym_rewritten_atom(
    base_atom_text: str,
    target_atom_text: str,
) -> str:
    """
    Rewrites target atom as a negation of base atom's predicate while preserving
    target atom's subject.

    Examples:
    base:   ahmed is happy.
    target: mohamed is sad.
    output: not mohamed is happy.

    base:   ahmed is good.
    target: sara is bad.
    output: not sara is good.
    """

    base_parts = _extract_subject_and_predicate(base_atom_text)
    target_parts = _extract_subject_and_predicate(target_atom_text)

    if base_parts is None or target_parts is None:
        return _normalize_atom_text(f"not {base_atom_text}")

    _, base_predicate = base_parts
    target_subject, _ = target_parts

    return _normalize_atom_text(f"not {target_subject} {base_predicate}")

def _predicate_relation_from_lexicon(
    atom_a_text: str,
    atom_b_text: str,
) -> Dict[str, str] | None:
    """
    Deterministic high-confidence predicate relation check.

    This is only for very direct English predicate synonym/antonym relations.
    It does not replace the LLM; it catches stable obvious cases before the LLM.
    """

    atom_a_parts = _extract_subject_and_predicate(atom_a_text)
    atom_b_parts = _extract_subject_and_predicate(atom_b_text)

    if atom_a_parts is None or atom_b_parts is None:
        return None

    _, predicate_a = atom_a_parts
    _, predicate_b = atom_b_parts

    predicate_a = predicate_a.strip()
    predicate_b = predicate_b.strip()

    synonym_predicate_pairs = {
        ("is big", "is large"),
        ("is closed", "is shut"),
        ("starts", "begins"),
        ("is happy", "is joyful"),
    }

    antonym_predicate_pairs = {
        ("is open", "is closed"),
        ("is on", "is off"),
        ("is alive", "is dead"),
        ("is active", "is inactive"),
        ("is good", "is bad"),
        ("is happy", "is sad"),
        ("passes", "fails"),
    }

    ordered_pair = (predicate_a, predicate_b)
    reversed_pair = (predicate_b, predicate_a)

    if ordered_pair in synonym_predicate_pairs or reversed_pair in synonym_predicate_pairs:
        return {
            "relation": "SYNONYM",
            "reason": "Direct predicate synonym found by deterministic lexical rule.",
        }

    if ordered_pair in antonym_predicate_pairs or reversed_pair in antonym_predicate_pairs:
        return {
            "relation": "ANTONYM",
            "reason": "Direct predicate antonym found by deterministic lexical rule.",
        }

    return None

def _is_state_vs_process_pair(
    atom_a_text: str,
    atom_b_text: str,
) -> bool:
    """
    Detects clear state-vs-change/process pairs.

    Example:
    the ground gets wet.
    the ground is wet.

    This must be AMBIGUOUS, not SYNONYM.
    """

    atom_a_parts = _extract_subject_and_predicate(atom_a_text)
    atom_b_parts = _extract_subject_and_predicate(atom_b_text)

    if atom_a_parts is None or atom_b_parts is None:
        return False

    _, predicate_a = atom_a_parts
    _, predicate_b = atom_b_parts

    a_words = predicate_a.split()
    b_words = predicate_b.split()

    if len(a_words) < 2 or len(b_words) < 2:
        return False

    process_starters = {"get", "gets", "become", "becomes"}
    state_starters = {"is", "are", "am", "was", "were"}

    a_process = a_words[0] in process_starters
    b_process = b_words[0] in process_starters

    a_state = a_words[0] in state_starters
    b_state = b_words[0] in state_starters

    # Same final property, different state/process type:
    # gets wet / is wet
    if a_process and b_state and a_words[-1] == b_words[-1]:
        return True

    if b_process and a_state and a_words[-1] == b_words[-1]:
        return True

    return False