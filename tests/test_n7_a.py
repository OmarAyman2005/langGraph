import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import (
    segment_and_validate_premises,
    build_normalized_prompt,
)
from normalizer.sentence_pattern_matcher import match_sentence_patterns
from normalizer.question_pattern_matcher import validate_question_pattern
from normalizer.subject_propagator import propagate_subjects
from normalizer.atom_extractor import extract_atoms_from_premises


TEST_CASES = [
    # ==================================================
    # EARLIER COMPONENT FAILURE CASES
    # ==================================================
    {
        "name": "empty input fails at N1",
        "input": "",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "no question mark fails at N2",
        "input": "Ahmed studies. Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "question only fails at N3",
        "input": "Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "unsupported premise fails at N4",
        "input": "All cats are animals. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "unsupported question target fails at N5",
        "input": "Ahmed studies. Is Ahmed taller than Sara?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },
    {
        "name": "ambiguous subject propagation fails at N6",
        "input": "Ahmed studies and he passes. Sara trains and she wins. Does he pass?",
        "expected_stage": "N6",
        "expected_success": False,
        "expected_error_contains": "Ambiguous subject propagation detected",
    },

    # ==================================================
    # VALID N7 CASES
    # ==================================================
    {
        "name": "extract atoms from facts",
        "input": "Ahmed studies. Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "sara sleeps.",
        ],
        "expected_occurrence_count": 2,
    },
    {
        "name": "extract atom from negation",
        "input": "Not Ahmed studies. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed studies.",
            "sara sleeps.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "sara sleeps.",
        ],
        "expected_occurrence_count": 2,
    },
    {
        "name": "extract atoms from conditional",
        "input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "ahmed passes.",
        ],
        "expected_occurrence_count": 3,
    },
    {
        "name": "extract atoms from conjunction",
        "input": "Ahmed studies and Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "sara sleeps.",
        ],
        "expected_occurrence_count": 2,
    },
    {
        "name": "extract atoms from disjunction",
        "input": "Ahmed studies or Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies or sara sleeps.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "sara sleeps.",
        ],
        "expected_occurrence_count": 2,
    },
    {
        "name": "extract atoms after subject propagation",
        "input": "If Ahmed plays, then he wins. He plays. Does he win?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed win?",
        "expected_premises": [
            "if ahmed plays, then ahmed wins.",
            "ahmed plays.",
        ],
        "expected_atoms": [
            "ahmed plays.",
            "ahmed wins.",
        ],
        "expected_occurrence_count": 3,
    },
    {
        "name": "extract atoms after missing subject propagation",
        "input": "Hany will travel or will stay home. Will Hany travel?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "will hany travel?",
        "expected_premises": [
            "hany will travel or hany will stay home.",
        ],
        "expected_atoms": [
            "hany will travel.",
            "hany will stay home.",
        ],
        "expected_occurrence_count": 2,
    },
    {
        "name": "duplicate atom appears once in atom table",
        "input": "Ahmed studies. If Ahmed studies, then Ahmed passes. Does Ahmed pass?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies.",
            "if ahmed studies, then ahmed passes.",
        ],
        "expected_atoms": [
            "ahmed studies.",
            "ahmed passes.",
        ],
        "expected_occurrence_count": 3,
    },
    {
        "name": "pronoun-only premises remain valid atoms",
        "input": "He played. He won. Did he win?",
        "expected_stage": "N7",
        "expected_success": True,
        "expected_question": "did he win?",
        "expected_premises": [
            "he played.",
            "he won.",
        ],
        "expected_atoms": [
            "he played.",
            "he won.",
        ],
        "expected_occurrence_count": 2,
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return expected.lower() in actual.lower()


def print_test_header(index: int, total: int, name: str, raw_input: str) -> None:
    print("=" * 80)
    print(f"TEST {index}/{total} — {name}")
    print("-" * 80)
    print("Input:")
    print(raw_input)


def print_expected(case: dict) -> None:
    print("\nExpected:")
    if case["expected_success"]:
        print("SUCCESS at N7")
        print(f"Question: {case.get('expected_question')}")
        print("Premises:")
        for premise in case.get("expected_premises", []):
            print(f"- {premise}")
        print("Atom Table:")
        for atom in case.get("expected_atoms", []):
            print(f"- {atom}")
        print(f"Occurrence Count: {case.get('expected_occurrence_count')}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(
    question: str,
    premises: list[str],
    atom_table: list[dict],
    atom_occurrences: list[dict],
    normalized_input: str,
) -> None:
    print("\nActual:")
    print("SUCCESS at N7")
    print(f"Question: {question}")

    print("Premises:")
    for premise in premises:
        print(f"- {premise}")

    print("Atom Table:")
    for atom in atom_table:
        print(f"- {atom['atom_id']}: {atom['atom_text']}")

    print("Atom Occurrences:")
    for occurrence in atom_occurrences:
        print(
            f"- Premise {occurrence['premise_index']} | "
            f"{occurrence['atom_id']} | "
            f"{occurrence['atom_text']}"
        )

    print("Normalized Input:")
    print(normalized_input)


def print_actual_failure(
    stage: str,
    error: str | None,
    failed_premises: list[str] | None = None,
) -> None:
    print("\nActual:")
    print(f"FAIL at {stage}")
    print(f"Error: {error}")

    if failed_premises:
        print("Failed Premises:")
        for premise in failed_premises:
            print(f"- {premise}")


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"], case["input"])
        print_expected(case)

        n1_result = unify_case(case["input"])

        if n1_result["success"] is False:
            actual_stage = "N1"
            actual_error = n1_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N1"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 raw result: {n1_result}")
            continue

        n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

        if n2_result["success"] is False:
            actual_stage = "N2"
            actual_error = n2_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N2"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
            continue

        n3_result = segment_and_validate_premises(
            n2_result["candidate_premise_text"]
        )

        if n3_result["success"] is False:
            actual_stage = "N3"
            actual_error = n3_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N3"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
            continue

        n4_result = match_sentence_patterns(n3_result["premises"])

        if n4_result["success"] is False:
            actual_stage = "N4"
            actual_error = n4_result.get("error")
            print_actual_failure(
                actual_stage,
                actual_error,
                n4_result.get("failed_premises", []),
            )

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N4"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
            continue

        n5_result = validate_question_pattern(n2_result["question"])

        if n5_result["success"] is False:
            actual_stage = "N5"
            actual_error = n5_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N5"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
            continue

        n6_result = propagate_subjects(
            premises=n4_result["pattern_matched_premises"],
            question=n2_result["question"],
        )

        if n6_result["success"] is False:
            actual_stage = "N6"
            actual_error = n6_result.get("error")
            print_actual_failure(
                actual_stage,
                actual_error,
                n6_result.get("failed_premises", []),
            )

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N6"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
                print(f"N6 raw result: {n6_result}")
            continue

        n7_result = extract_atoms_from_premises(
            n6_result["subject_propagated_premises"]
        )

        if n7_result["success"] is False:
            actual_stage = "N7"
            actual_error = n7_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N7"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
                print(f"N6 raw result: {n6_result}")
                print(f"N7 raw result: {n7_result}")
            continue

        actual_question = n6_result["subject_propagated_question"]
        actual_premises = n6_result["subject_propagated_premises"]
        actual_atoms = [atom["atom_text"] for atom in n7_result["atom_table"]]
        actual_occurrence_count = len(n7_result["atom_occurrences"])

        actual_normalized_input = build_normalized_prompt(
            premises=actual_premises,
            question=actual_question,
        )

        print_actual_success(
            question=actual_question,
            premises=actual_premises,
            atom_table=n7_result["atom_table"],
            atom_occurrences=n7_result["atom_occurrences"],
            normalized_input=actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")
        atoms_ok = actual_atoms == case.get("expected_atoms")
        occurrence_count_ok = actual_occurrence_count == case.get(
            "expected_occurrence_count"
        )

        if (
            success_ok
            and question_ok
            and premises_ok
            and atoms_ok
            and occurrence_count_ok
        ):
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"N1 output: {n1_result.get('case_unified_input')}")
            print(f"N2 raw result: {n2_result}")
            print(f"N3 raw result: {n3_result}")
            print(f"N4 raw result: {n4_result}")
            print(f"N5 raw result: {n5_result}")
            print(f"N6 raw result: {n6_result}")
            print(f"N7 raw result: {n7_result}")
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()