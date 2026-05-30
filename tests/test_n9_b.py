import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
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


def read_multiline_input() -> str:
    print("Manual Test: Normalizer N1 + N2 + N3 + N4 + N5 + N6 + N7 + N8 + N9")
    print("N9: Semantic Relation Handler")
    print("Uses the normalizer LLM model from config, expected: qwen2.5:14b")
    print("Paste one raw input.")
    print("When finished, type END on a new line.")
    print("=" * 80)

    lines = []

    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def print_errors(result: dict) -> None:
    for error in result.get("errors", []):
        print(f"- {error}")


def main() -> None:
    raw_input = read_multiline_input()

    print("\n" + "=" * 80)
    print("RAW INPUT:")
    print(raw_input)

    print("\n" + "-" * 80)
    print("N1 — CHARACTER ADJUSTER")

    n1_result = unify_case(raw_input)

    if n1_result["success"] is False:
        print("Status: FAILED")
        print_errors(n1_result)
        print("\nFinal Result: FAILED at N1")
        return

    print("Status: PASSED")
    print(n1_result["case_unified_input"])

    print("\n" + "-" * 80)
    print("N2 — QUESTION DETECTOR")

    n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

    if n2_result["success"] is False:
        print("Status: FAILED")
        print_errors(n2_result)
        print("\nFinal Result: FAILED at N2")
        return

    print("Status: PASSED")
    print("Question:")
    print(n2_result["question"])

    print("\nCandidate Premise Text:")
    print(n2_result["candidate_premise_text"])

    print("\n" + "-" * 80)
    print("N3 — PREMISES SEPARATOR")

    n3_result = segment_and_validate_premises(
        n2_result["candidate_premise_text"]
    )

    if n3_result["success"] is False:
        print("Status: FAILED")
        print_errors(n3_result)
        print("\nFinal Result: FAILED at N3")
        return

    print("Status: PASSED")
    for i, premise in enumerate(n3_result["premises"], start=1):
        print(f"{i}. {premise}")

    print("\n" + "-" * 80)
    print("N4 — SENTENCE PATTERN MATCHER")

    n4_result = match_sentence_patterns(n3_result["premises"])

    if n4_result["success"] is False:
        print("Status: FAILED")
        print_errors(n4_result)

        failed_premises = n4_result.get("failed_premises", [])
        if failed_premises:
            print("\nFailed Premise(s):")
            for premise in failed_premises:
                print(f"- {premise}")

        print("\nFinal Result: FAILED at N4")
        return

    print("Status: PASSED")
    for i, premise in enumerate(n4_result["pattern_matched_premises"], start=1):
        print(f"{i}. {premise}")

    print("\n" + "-" * 80)
    print("N5 — QUESTION PATTERN MATCHER")

    n5_result = validate_question_pattern(n2_result["question"])

    if n5_result["success"] is False:
        print("Status: FAILED")
        print_errors(n5_result)
        print("\nFinal Result: FAILED at N5")
        return

    print("Status: PASSED")
    print("Target Candidate(s) Before Subject Propagation:")
    for i, target in enumerate(n5_result["target_candidates"], start=1):
        print(f"{i}. {target}")

    print("\n" + "-" * 80)
    print("N6 — SUBJECT PROPAGATION")

    n6_result = propagate_subjects(
        premises=n4_result["pattern_matched_premises"],
        question=n2_result["question"],
    )

    if n6_result["success"] is False:
        print("Status: FAILED")
        print_errors(n6_result)

        failed_premises = n6_result.get("failed_premises", [])
        if failed_premises:
            print("\nFailed Premise(s):")
            for premise in failed_premises:
                print(f"- {premise}")

        print("\nFinal Result: FAILED at N6")
        return

    print("Status: PASSED")
    print("Subject-Propagated Premises:")
    for i, premise in enumerate(n6_result["subject_propagated_premises"], start=1):
        print(f"{i}. {premise}")

    print("\nSubject-Propagated Question:")
    print(n6_result["subject_propagated_question"])

    half_normalized_prompt = build_normalized_prompt(
        premises=n6_result["subject_propagated_premises"],
        question=n6_result["subject_propagated_question"],
    )

    print("\n" + "-" * 80)
    print("N7 — EXTRACTING ATOMS FROM PREMISES")

    n7_result = extract_atoms_from_premises(
        n6_result["subject_propagated_premises"]
    )

    if n7_result["success"] is False:
        print("Status: FAILED")
        print_errors(n7_result)
        print("\nFinal Result: FAILED at N7")
        return

    print("Status: PASSED")
    print("Premise Atom Table:")
    for atom in n7_result["atom_table"]:
        print(f"{atom['atom_id']}. {atom['atom_text']}")

    print("\n" + "-" * 80)
    print("N8 — EXTRACTING TARGET ATOM(S) FROM QUESTION")

    n8_result = extract_target_atoms_from_question(
        question=n6_result["subject_propagated_question"],
        existing_atom_table=n7_result["atom_table"],
    )

    if n8_result["success"] is False:
        print("Status: FAILED")
        print_errors(n8_result)
        print("\nFinal Result: FAILED at N8")
        return

    print("Status: PASSED")
    print("Atom Table Before Semantic Relation Handling:")
    for atom in n8_result["atom_table"]:
        print(f"{atom['atom_id']}. {atom['atom_text']}")

    print("\n" + "-" * 80)
    print("N9 — SEMANTIC RELATION HANDLER")

    n9_result = handle_semantic_relations(
        atom_table=n8_result["atom_table"],
        half_normalized_prompt=half_normalized_prompt,
        premises=n6_result["subject_propagated_premises"],
        question=n6_result["subject_propagated_question"],
        target_atoms=n8_result["target_atoms"],
    )

    if n9_result["success"] is False:
        print("Status: FAILED")
        print_errors(n9_result)

        ambiguous_pair = n9_result.get("ambiguous_pair")
        if ambiguous_pair:
            print("\nAmbiguous Pair:")
            print(f"{ambiguous_pair['atom_a_id']}: {ambiguous_pair['atom_a_text']}")
            print(f"{ambiguous_pair['atom_b_id']}: {ambiguous_pair['atom_b_text']}")
            print(f"Reason: {ambiguous_pair['reason']}")

        print("\nLLM/Deterministic Comparison(s) Before Failure:")
        for comparison in n9_result.get("comparisons", []):
            print(
                f"- {comparison['atom_a_id']} vs {comparison['atom_b_id']} | "
                f"{comparison['relation']} | {comparison['reason']}"
            )

        print("\nFinal Result: FAILED at N9")
        return

    print("Status: PASSED")

    print("\nAtom Table After Semantic Relation Handling:")
    for atom in n9_result["atom_table"]:
        print(f"{atom['atom_id']}. {atom['atom_text']}")

    print("\nCanonical Atom Table:")
    for atom in n9_result["canonical_atom_table"]:
        print(f"{atom['atom_id']}. {atom['atom_text']}")

    print("\nAtom ID Map:")
    for atom_id, canonical_id in n9_result["atom_id_map"].items():
        print(f"{atom_id} -> {canonical_id}")

    print("\nSemantic Pair(s):")
    if n9_result["semantic_pairs"]:
        for pair in n9_result["semantic_pairs"]:
            if pair["relation"] == "SYNONYM":
                print(
                    f"- SYNONYM: {pair['replaced_atom_id']} "
                    f"({pair['original_replaced_atom_text']}) "
                    f"-> {pair['kept_atom_id']} "
                    f"({pair['kept_atom_text']})"
                )
            elif pair["relation"] == "ANTONYM":
                print(
                    f"- ANTONYM: {pair['negated_atom_id']} "
                    f"({pair['original_negated_atom_text']}) "
                    f"-> {pair['new_negated_atom_text']}"
                )
    else:
        print("- None")

    print("\nSynonym Pair(s):")
    if n9_result["synonym_pairs"]:
        for pair in n9_result["synonym_pairs"]:
            print(
                f"- {pair['replaced_atom_id']} "
                f"({pair['original_replaced_atom_text']}) "
                f"-> {pair['kept_atom_id']} "
                f"({pair['kept_atom_text']})"
            )
    else:
        print("- None")

    print("\nAntonym Pair(s):")
    if n9_result["antonym_pairs"]:
        for pair in n9_result["antonym_pairs"]:
            print(
                f"- {pair['negated_atom_id']} "
                f"({pair['original_negated_atom_text']}) "
                f"-> {pair['new_negated_atom_text']}"
            )
    else:
        print("- None")

    print("\nLLM/Deterministic Comparison(s):")
    for comparison in n9_result["comparisons"]:
        print(
            f"- {comparison['atom_a_id']} vs {comparison['atom_b_id']} | "
            f"{comparison['relation']} | {comparison['reason']}"
        )

    print("\nHalf-Normalized Input Before Semantic Relation Handling:")
    print(half_normalized_prompt)

    print("\nSemantic-Unified Normalized Input:")
    print(n9_result["semantic_unified_prompt"])

    print("\nFinal Result: PASSED N1 + N2 + N3 + N4 + N5 + N6 + N7 + N8 + N9")


if __name__ == "__main__":
    main()