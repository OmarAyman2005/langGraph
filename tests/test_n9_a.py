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


TEST_CASES = [
    {
        "name": "direct adjective synonym unified",
        "input": "Ahmed is big. Is Ahmed large?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is big.",
        ],
        "expected_question": "is ahmed big?",
    },
    {
        "name": "closed and shut synonym unified",
        "input": "The door is closed. Is the door shut?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "the door is closed.",
        ],
        "expected_question": "is the door closed?",
    },
    {
        "name": "state versus process ambiguous",
        "input": "The ground gets wet. Is the ground wet?",
        "expected_success": False,
        "expected_stage": "N9",
        "expected_error_contains": "Ambiguous semantic relationship detected",
    },
    {
        "name": "present simple versus continuous ambiguous",
        "input": "It rains. Is it raining?",
        "expected_success": False,
        "expected_stage": "N9",
        "expected_error_contains": "Ambiguous semantic relationship detected",
    },
    {
        "name": "present versus past no relation",
        "input": "It rains. Did it rain?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "it rains.",
            "it did rain.",
        ],
        "expected_question": "did it rain?",
    },
    {
        "name": "do-support alternatives unified",
        "input": "Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed studies.",
            "ahmed passes.",
        ],
        "expected_question": "does ahmed pass?",
    },
    {
        "name": "related adjective no relation while real synonym unifies",
        "input": "Ahmed is big. He is great. Is Ahmed large?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is big.",
            "ahmed is great.",
        ],
        "expected_question": "is ahmed big?",
    },
    {
        "name": "different positive descriptions no relation",
        "input": "Ahmed is amazing. Salwa is crazy. Is Ahmed nice?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is amazing.",
            "salwa is crazy.",
            "ahmed is nice.",
        ],
        "expected_question": "is ahmed nice?",
    },
    {
        "name": "same subject antonym relation",
        "input": "The door is open. Is the door closed?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "the door is open.",
            "not the door is open.",
        ],
        "expected_question": "is the door not open?",
    },
    {
        "name": "process synonym unified",
        "input": "The machine starts. Does the machine begin?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "the machine starts.",
        ],
        "expected_question": "does the machine start?",
    },
    {
        "name": "different subject synonym predicate preserves target subject",
        "input": "Ahmed is happy. Mohamed is joyful. Is Ahmed happy?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is happy.",
            "mohamed is happy.",
        ],
        "expected_question": "is ahmed happy?",
    },
    {
        "name": "different subject antonym predicate preserves target subject",
        "input": "Ahmed is happy. Mohamed is sad. Is Ahmed happy?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is happy.",
            "not mohamed is happy.",
        ],
        "expected_question": "is ahmed happy?",
    },
    {
        "name": "different subject good bad antonym preserves target subject",
        "input": "Ahmed is good. Sara is bad. Is Ahmed good?",
        "expected_success": True,
        "expected_stage": "N9",
        "expected_canonical_atoms": [
            "ahmed is good.",
            "not sara is good.",
        ],
        "expected_question": "is ahmed good?",
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return expected.lower() in actual.lower()


def run_pipeline_until_n9(raw_input: str) -> tuple[str, dict]:
    n1_result = unify_case(raw_input)

    if n1_result["success"] is False:
        return "N1", n1_result

    n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

    if n2_result["success"] is False:
        return "N2", n2_result

    n3_result = segment_and_validate_premises(
        n2_result["candidate_premise_text"]
    )

    if n3_result["success"] is False:
        return "N3", n3_result

    n4_result = match_sentence_patterns(n3_result["premises"])

    if n4_result["success"] is False:
        return "N4", n4_result

    n5_result = validate_question_pattern(n2_result["question"])

    if n5_result["success"] is False:
        return "N5", n5_result

    n6_result = propagate_subjects(
        premises=n4_result["pattern_matched_premises"],
        question=n2_result["question"],
    )

    if n6_result["success"] is False:
        return "N6", n6_result

    n7_result = extract_atoms_from_premises(
        n6_result["subject_propagated_premises"]
    )

    if n7_result["success"] is False:
        return "N7", n7_result

    n8_result = extract_target_atoms_from_question(
        question=n6_result["subject_propagated_question"],
        existing_atom_table=n7_result["atom_table"],
    )

    if n8_result["success"] is False:
        return "N8", n8_result

    half_normalized_prompt = build_normalized_prompt(
        premises=n6_result["subject_propagated_premises"],
        question=n6_result["subject_propagated_question"],
    )

    n9_result = handle_semantic_relations(
        atom_table=n8_result["atom_table"],
        half_normalized_prompt=half_normalized_prompt,
        premises=n6_result["subject_propagated_premises"],
        question=n6_result["subject_propagated_question"],
        target_atoms=n8_result["target_atoms"],
    )

    return "N9", {
        "success": n9_result["success"],
        "n6": n6_result,
        "n7": n7_result,
        "n8": n8_result,
        "n9": n9_result,
        "error": n9_result.get("error"),
        "errors": n9_result.get("errors", []),
    }


def print_test_header(index: int, total: int, name: str, raw_input: str) -> None:
    print("=" * 80)
    print(f"TEST {index}/{total} — {name}")
    print("-" * 80)
    print("Input:")
    print(raw_input)


def print_n9_success(result: dict) -> None:
    n9 = result["n9"]

    print("\nActual:")
    print("SUCCESS at N9")

    print("\nAtom Table After Semantic Handling:")
    for atom in n9["atom_table"]:
        print(f"- {atom['atom_id']}: {atom['atom_text']}")

    print("\nCanonical Atom Table:")
    for atom in n9["canonical_atom_table"]:
        print(f"- {atom['atom_id']}: {atom['atom_text']}")

    print("\nSemantic Pair(s):")
    if n9["semantic_pairs"]:
        for pair in n9["semantic_pairs"]:
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

    print("\nLLM/Deterministic Comparison(s):")
    for comparison in n9["comparisons"]:
        print(
            f"- {comparison['atom_a_id']} vs {comparison['atom_b_id']} | "
            f"{comparison['relation']} | {comparison['reason']}"
        )

    print("\nSemantic-Unified Normalized Input:")
    print(n9["semantic_unified_prompt"])


def print_failure(stage: str, result: dict) -> None:
    print("\nActual:")
    print(f"FAIL at {stage}")
    print(f"Error: {result.get('error')}")

    n9 = result.get("n9")
    if n9 and n9.get("ambiguous_pair"):
        pair = n9["ambiguous_pair"]
        print("\nAmbiguous Pair:")
        print(f"- {pair['atom_a_id']}: {pair['atom_a_text']}")
        print(f"- {pair['atom_b_id']}: {pair['atom_b_text']}")
        print(f"Reason: {pair['reason']}")

    if n9 and n9.get("comparisons"):
        print("\nComparison(s) Before Failure:")
        for comparison in n9["comparisons"]:
            print(
                f"- {comparison['atom_a_id']} vs {comparison['atom_b_id']} | "
                f"{comparison['relation']} | {comparison['reason']}"
            )


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"], case["input"])

        stage, result = run_pipeline_until_n9(case["input"])

        if result["success"] is False:
            print_failure(stage, result)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == stage
            error_ok = contains(result.get("error"), case.get("expected_error_contains"))

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(result)

            continue

        print_n9_success(result)

        n9 = result["n9"]

        actual_canonical_atoms = [
            atom["atom_text"]
            for atom in n9["canonical_atom_table"]
        ]

        actual_question = n9["semantic_unified_question"]

        success_ok = case["expected_success"] is True
        atoms_ok = actual_canonical_atoms == case.get("expected_canonical_atoms")
        question_ok = actual_question == case.get("expected_question")

        if success_ok and atoms_ok and question_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"Actual canonical atoms: {actual_canonical_atoms}")
            print(f"Expected canonical atoms: {case.get('expected_canonical_atoms')}")
            print(f"Actual question: {actual_question}")
            print(f"Expected question: {case.get('expected_question')}")
            print(result)

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()