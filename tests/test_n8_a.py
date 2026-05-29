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
from normalizer.target_atom_extractor import extract_target_atoms_from_question


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
    # VALID N8 CASES
    # ==================================================
    {
        "name": "extract target from is-question already in atom table",
        "input": "The sensor is active. Is the sensor active?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "is the sensor active?",
        "expected_premises": ["the sensor is active."],
        "expected_premise_atoms": ["the sensor is active."],
        "expected_target_atoms": ["the sensor is active."],
        "expected_final_atoms": ["the sensor is active."],
    },
    {
        "name": "extract target from is-question new atom",
        "input": "Ahmed studies. Is Ahmed happy?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "is ahmed happy?",
        "expected_premises": ["ahmed studies."],
        "expected_premise_atoms": ["ahmed studies."],
        "expected_target_atoms": ["ahmed is happy."],
        "expected_final_atoms": ["ahmed studies.", "ahmed is happy."],
    },
    {
        "name": "extract target from does-question with two target atoms",
        "input": "Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": ["ahmed studies."],
        "expected_premise_atoms": ["ahmed studies."],
        "expected_target_atoms": [
            "ahmed passes.",
            "ahmed does pass.",
        ],
        "expected_final_atoms": [
            "ahmed studies.",
            "ahmed passes.",
            "ahmed does pass.",
        ],
    },
    {
        "name": "extract target from do-question with two target atoms",
        "input": "They play. Do they play?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "do they play?",
        "expected_premises": ["they play."],
        "expected_premise_atoms": ["they play."],
        "expected_target_atoms": [
            "they play.",
            "they do play.",
        ],
        "expected_final_atoms": [
            "they play.",
            "they do play.",
        ],
    },
    {
        "name": "extract target from did-question",
        "input": "Ahmed played. Did Ahmed win?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "did ahmed win?",
        "expected_premises": ["ahmed played."],
        "expected_premise_atoms": ["ahmed played."],
        "expected_target_atoms": ["ahmed did win."],
        "expected_final_atoms": [
            "ahmed played.",
            "ahmed did win.",
        ],
    },
    {
        "name": "extract target from modal question",
        "input": "Ahmed trains. Will Ahmed win?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "will ahmed win?",
        "expected_premises": ["ahmed trains."],
        "expected_premise_atoms": ["ahmed trains."],
        "expected_target_atoms": ["ahmed will win."],
        "expected_final_atoms": [
            "ahmed trains.",
            "ahmed will win.",
        ],
    },
    {
        "name": "extract target after subject propagation",
        "input": "If Ahmed plays, then he wins. He plays. Does he win?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "does ahmed win?",
        "expected_premises": [
            "if ahmed plays, then ahmed wins.",
            "ahmed plays.",
        ],
        "expected_premise_atoms": [
            "ahmed plays.",
            "ahmed wins.",
        ],
        "expected_target_atoms": [
            "ahmed wins.",
            "ahmed does win.",
        ],
        "expected_final_atoms": [
            "ahmed plays.",
            "ahmed wins.",
            "ahmed does win.",
        ],
    },
    {
        "name": "extract target from pronoun-only prompt unchanged",
        "input": "He played. He won. Did he win?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "did he win?",
        "expected_premises": [
            "he played.",
            "he won.",
        ],
        "expected_premise_atoms": [
            "he played.",
            "he won.",
        ],
        "expected_target_atoms": [
            "he did win.",
        ],
        "expected_final_atoms": [
            "he played.",
            "he won.",
            "he did win.",
        ],
    },
    {
        "name": "extract target from modal question with multi-word predicate",
        "input": "Ahmed is good. Sara is not nice. Will Hla play well?",
        "expected_stage": "N8",
        "expected_success": True,
        "expected_question": "will hla play well?",
        "expected_premises": [
            "ahmed is good.",
            "not sara is nice.",
        ],
        "expected_premise_atoms": [
            "ahmed is good.",
            "sara is nice.",
        ],
        "expected_target_atoms": [
            "hla will play well.",
        ],
        "expected_final_atoms": [
            "ahmed is good.",
            "sara is nice.",
            "hla will play well.",
        ],
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
        print("SUCCESS at N8")
        print(f"Question: {case.get('expected_question')}")
        print("Premise Atoms:")
        for atom in case.get("expected_premise_atoms", []):
            print(f"- {atom}")
        print("Target Atom(s):")
        for atom in case.get("expected_target_atoms", []):
            print(f"- {atom}")
        print("Final Atom Table:")
        for atom in case.get("expected_final_atoms", []):
            print(f"- {atom}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(
    question: str,
    premises: list[str],
    premise_atom_table: list[dict],
    target_atoms: list[dict],
    final_atom_table: list[dict],
    normalized_input: str,
) -> None:
    print("\nActual:")
    print("SUCCESS at N8")
    print(f"Question: {question}")

    print("Premises:")
    for premise in premises:
        print(f"- {premise}")

    print("Premise Atom Table:")
    for atom in premise_atom_table:
        print(f"- {atom['atom_id']}: {atom['atom_text']}")

    print("Target Atom(s):")
    for target in target_atoms:
        print(f"- {target['atom_id']}: {target['atom_text']}")

    print("Final Atom Table:")
    for atom in final_atom_table:
        print(f"- {atom['atom_id']}: {atom['atom_text']}")

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

        n8_result = extract_target_atoms_from_question(
            question=n6_result["subject_propagated_question"],
            existing_atom_table=n7_result["atom_table"],
        )

        if n8_result["success"] is False:
            actual_stage = "N8"
            actual_error = n8_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N8"
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
                print(f"N8 raw result: {n8_result}")
            continue

        actual_question = n6_result["subject_propagated_question"]
        actual_premises = n6_result["subject_propagated_premises"]
        actual_premise_atoms = [atom["atom_text"] for atom in n7_result["atom_table"]]
        actual_target_atoms = [atom["atom_text"] for atom in n8_result["target_atoms"]]
        actual_final_atoms = [atom["atom_text"] for atom in n8_result["atom_table"]]

        actual_normalized_input = build_normalized_prompt(
            premises=actual_premises,
            question=actual_question,
        )

        print_actual_success(
            question=actual_question,
            premises=actual_premises,
            premise_atom_table=n7_result["atom_table"],
            target_atoms=n8_result["target_atoms"],
            final_atom_table=n8_result["atom_table"],
            normalized_input=actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")
        premise_atoms_ok = actual_premise_atoms == case.get("expected_premise_atoms")
        target_atoms_ok = actual_target_atoms == case.get("expected_target_atoms")
        final_atoms_ok = actual_final_atoms == case.get("expected_final_atoms")

        if (
            success_ok
            and question_ok
            and premises_ok
            and premise_atoms_ok
            and target_atoms_ok
            and final_atoms_ok
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
            print(f"N8 raw result: {n8_result}")
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()