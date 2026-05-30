from typing import Any, Dict

from normalizer.case_unifier import unify_case
from normalizer.errors import make_error
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import (
    build_normalized_prompt,
    segment_and_validate_premises,
)
from normalizer.sentence_pattern_matcher import match_sentence_patterns
from normalizer.question_pattern_matcher import validate_question_pattern
from normalizer.subject_propagator import propagate_subjects
from normalizer.atom_extractor import extract_atoms_from_premises
from normalizer.target_atom_extractor import extract_target_atoms_from_question
from normalizer.semantic_relation_handler import handle_semantic_relations


def normalize_raw_prompt(raw_input: str) -> Dict[str, Any]:
    """
    Full Normalizer Pipeline.

    Current finalized normalizer order:

    N1 — Character Adjuster / Case Unifier
    N2 — Question Detector
    N3 — Premises Separator
    N4 — Sentence Pattern Matcher
    N5 — Question Pattern Matcher
    N6 — Subject Propagation
    N7 — Extracting Atoms From Premises
    N8 — Extracting Target Atom(s) From Question
    N9 — Semantic Relation Handler

    Note:
    N9 replaces the old separated synonym/antonym unifiers.
    """

    # ==================================================
    # N1 — Character Adjuster / Case Unifier
    # ==================================================
    n1_result = unify_case(raw_input)

    if not n1_result["success"]:
        return make_error(n1_result["error"])

    case_unified_input = n1_result["case_unified_input"]

    # ==================================================
    # N2 — Question Detector
    # ==================================================
    n2_result = detect_single_yes_no_question(case_unified_input)

    if not n2_result["success"]:
        return make_error(n2_result["error"])

    detected_question = n2_result["question"]
    candidate_premise_text = n2_result["candidate_premise_text"]

    # ==================================================
    # N3 — Premises Separator
    # ==================================================
    n3_result = segment_and_validate_premises(candidate_premise_text)

    if not n3_result["success"]:
        return make_error(n3_result["error"])

    separated_premises = n3_result["premises"]

    # ==================================================
    # N4 — Sentence Pattern Matcher
    # ==================================================
    n4_result = match_sentence_patterns(separated_premises)

    if not n4_result["success"]:
        return make_error(n4_result["error"])

    pattern_matched_premises = n4_result["pattern_matched_premises"]

    # ==================================================
    # N5 — Question Pattern Matcher
    # ==================================================
    n5_result = validate_question_pattern(detected_question)

    if not n5_result["success"]:
        return make_error(n5_result["error"])

    # ==================================================
    # N6 — Subject Propagation
    # ==================================================
    n6_result = propagate_subjects(
        premises=pattern_matched_premises,
        question=detected_question,
    )

    if not n6_result["success"]:
        return make_error(n6_result["error"])

    subject_propagated_premises = n6_result["subject_propagated_premises"]
    subject_propagated_question = n6_result["subject_propagated_question"]

    half_normalized_prompt = build_normalized_prompt(
        premises=subject_propagated_premises,
        question=subject_propagated_question,
    )

    # ==================================================
    # N7 — Extracting Atoms From Premises
    # ==================================================
    n7_result = extract_atoms_from_premises(subject_propagated_premises)

    if not n7_result["success"]:
        return make_error(n7_result["error"])

    # ==================================================
    # N8 — Extracting Target Atom(s) From Question
    # ==================================================
    n8_result = extract_target_atoms_from_question(
        question=subject_propagated_question,
        existing_atom_table=n7_result["atom_table"],
    )

    if not n8_result["success"]:
        return make_error(n8_result["error"])

    # ==================================================
    # N9 — Semantic Relation Handler
    # ==================================================
    n9_result = handle_semantic_relations(
        atom_table=n8_result["atom_table"],
        half_normalized_prompt=half_normalized_prompt,
        premises=subject_propagated_premises,
        question=subject_propagated_question,
        target_atoms=n8_result["target_atoms"],
    )

    if not n9_result["success"]:
        return make_error(n9_result["error"])

    final_normalized_input = n9_result["semantic_unified_prompt"]

    return {
        "success": True,
        "normalized_input": final_normalized_input,
        "error": None,
        "debug": {
            "n1_case_unification": n1_result,
            "n2_question_detection": n2_result,
            "n3_premise_segmentation": n3_result,
            "n4_sentence_pattern_matching": n4_result,
            "n5_question_pattern_matching": n5_result,
            "n6_subject_propagation": n6_result,
            "n7_atom_extraction": n7_result,
            "n8_target_atom_extraction": n8_result,
            "n9_semantic_relation_handling": n9_result,
            "half_normalized_prompt_before_semantic_handling": half_normalized_prompt,
            "final_premises": n9_result["semantic_unified_premises"],
            "final_question": n9_result["semantic_unified_question"],
            "final_atom_table": n9_result["canonical_atom_table"],
            "full_atom_table_after_semantic_handling": n9_result["atom_table"],
            "atom_id_map": n9_result["atom_id_map"],
            "semantic_pairs": n9_result["semantic_pairs"],
            "synonym_pairs": n9_result["synonym_pairs"],
            "antonym_pairs": n9_result["antonym_pairs"],
            "semantic_comparisons": n9_result["comparisons"],
        },
    }