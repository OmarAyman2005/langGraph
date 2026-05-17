from typing import Any, Dict

from normalizer.case_unifier import unify_case
from normalizer.errors import make_error
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import segment_and_validate_premises
from normalizer.pattern_normalizer import normalize_sentence_patterns
from normalizer.atom_extractor import create_atom_table, proposition_to_question
from normalizer.atom_unifier import (
    analyze_atom_relations_with_llm,
    build_atom_mapping,
    rebuild_premise,
)


def normalize_raw_prompt(raw_input: str) -> Dict[str, Any]:
    case_result = unify_case(raw_input)

    if not case_result["success"]:
        return make_error(case_result["error"])

    case_unified_input = case_result["case_unified_input"]

    question_result = detect_single_yes_no_question(case_unified_input)

    if not question_result["success"]:
        return make_error(question_result["error"])

    raw_question = question_result["question"]
    candidate_premise_text = question_result["candidate_premise_text"]

    premise_result = segment_and_validate_premises(candidate_premise_text)

    if not premise_result["success"]:
        return make_error(premise_result["error"])

    raw_premises = premise_result["premises"]

    pattern_result = normalize_sentence_patterns(raw_premises)

    if not pattern_result["success"]:
        return make_error(pattern_result["error"])

    normalized_premises = pattern_result["premises"]

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
            "case_unification": case_result.get("debug", {}),
            "question": raw_question,
            "raw_premises": raw_premises,
            "normalized_premises_before_atom_unification": normalized_premises,
            "atom_table": atom_table,
            "relation_result": relation_result,
            "atom_mapping": atom_mapping,
        },
    }
