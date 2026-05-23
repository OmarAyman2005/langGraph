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


TEST_CASES = [
    # ==================================================
    # N1 FAILURE CASES
    # ==================================================
    {
        "name": "empty input fails at N1",
        "input": "",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "non-English input fails at N1",
        "input": "Ahmed studies 😊. Does Ahmed pass?",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊",
    },
    {
        "name": "unsupported character fails at N1",
        "input": "Ahmed studies @ school. Does Ahmed pass?",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: @",
    },

    # ==================================================
    # N2 FAILURE CASES
    # ==================================================
    {
        "name": "no question mark fails at N2",
        "input": "Ahmed studies. Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "two yes-no questions fail at N2",
        "input": "Ahmed studies. Does Ahmed pass? Is Sara happy?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
        "name": "wh question fails at N2",
        "input": "Ahmed studies. What does Ahmed do?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },

    # ==================================================
    # N3 FAILURE CASES
    # ==================================================
    {
        "name": "question only fails at N3 because no premises remain",
        "input": "Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "question at beginning with no later premises fails at N3",
        "input": "Is Ahmed happy?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },

    # ==================================================
    # VALID N3 CASES — question at end
    # ==================================================
    {
        "name": "one premise before question",
        "input": "Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies.",
        "expected_premises": ["ahmed studies."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "two premises before question",
        "input": "Ahmed studies. Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps.",
        "expected_premises": ["ahmed studies.", "sara sleeps."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "three premises before question",
        "input": "Ahmed studies. Sara sleeps. The ground is wet. Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps. the ground is wet.",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
            "the ground is wet.",
        ],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "3. the ground is wet.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "conditional premise before question",
        "input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "if ahmed studies, then ahmed passes. ahmed studies.",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
        "expected_normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },

    # ==================================================
    # VALID N3 CASES — question at beginning
    # ==================================================
    {
        "name": "question at beginning with one premise after it",
        "input": "Does Ahmed pass? Ahmed studies.",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies.",
        "expected_premises": ["ahmed studies."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "question at beginning with two premises after it",
        "input": "Is Ahmed happy? Ahmed studies. Sara sleeps.",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "is ahmed happy?",
        "expected_candidate": "ahmed studies. sara sleeps.",
        "expected_premises": ["ahmed studies.", "sara sleeps."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "is ahmed happy?"
        ),
    },

    # ==================================================
    # VALID N3 CASES — question in middle
    # ==================================================
    {
        "name": "question in middle with premises before and after",
        "input": "Ahmed studies. Does Ahmed pass? Sara sleeps.",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps.",
        "expected_premises": ["ahmed studies.", "sara sleeps."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "question in middle with multiple premises before and after",
        "input": "Ahmed studies. Sara sleeps. Is Ahmed happy? The ground is wet. The door is open.",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "is ahmed happy?",
        "expected_candidate": "ahmed studies. sara sleeps. the ground is wet. the door is open.",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
            "the ground is wet.",
            "the door is open.",
        ],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "3. the ground is wet.\n"
            "4. the door is open.\n"
            "\n"
            "Question:\n"
            "is ahmed happy?"
        ),
    },

    # ==================================================
    # VALID N3 CASES — line-separated / mixed formatting
    # ==================================================
    {
        "name": "premises on separate lines",
        "input": "Ahmed studies.\nSara sleeps.\nDoes Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps.",
        "expected_premises": ["ahmed studies.", "sara sleeps."],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
    },
    {
        "name": "mixed same-line and separate-line premises",
        "input": "Ahmed studies. Sara sleeps.\nThe ground is wet.\nDoes Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps. the ground is wet.",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
            "the ground is wet.",
        ],
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "3. the ground is wet.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
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
        print("SUCCESS at N3")
        print(f"Question: {case.get('expected_question')}")
        print("Separated Premises:")
        for premise in case.get("expected_premises", []):
            print(f"- {premise}")
        print("Normalized Input:")
        print(case.get("expected_normalized_input"))
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(
    question: str,
    premises: list[str],
    normalized_input: str,
) -> None:
    print("\nActual:")
    print("SUCCESS at N3")
    print(f"Question: {question}")
    print("Separated Premises:")
    for premise in premises:
        print(f"- {premise}")
    print("Normalized Input:")
    print(normalized_input)


def print_actual_failure(stage: str, error: str | None) -> None:
    print("\nActual:")
    print(f"FAIL at {stage}")
    print(f"Error: {error}")


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"], case["input"])
        print_expected(case)

        # -------------------------------
        # N1
        # -------------------------------
        n1_result = unify_case(case["input"])

        if n1_result["success"] is False:
            actual_stage = "N1"
            actual_error = n1_result.get("error")

            print_actual_failure(actual_stage, actual_error)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N1"
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 raw result: {n1_result}")
            continue

        # -------------------------------
        # N2
        # -------------------------------
        n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

        if n2_result["success"] is False:
            actual_stage = "N2"
            actual_error = n2_result.get("error")

            print_actual_failure(actual_stage, actual_error)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N2"
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
            continue

        # -------------------------------
        # N3
        # -------------------------------
        n3_result = segment_and_validate_premises(
            n2_result["candidate_premise_text"]
        )

        if n3_result["success"] is False:
            actual_stage = "N3"
            actual_error = n3_result.get("error")

            print_actual_failure(actual_stage, actual_error)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N3"
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
            continue

        actual_question = n2_result.get("question")
        actual_premises = n3_result.get("premises")
        actual_normalized_input = build_normalized_prompt(
            actual_premises,
            actual_question,
        )

        print_actual_success(
            actual_question,
            actual_premises,
            actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")
        normalized_ok = actual_normalized_input == case.get("expected_normalized_input")

        if success_ok and question_ok and premises_ok and normalized_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"N1 output: {n1_result.get('case_unified_input')}")
            print(f"N2 raw result: {n2_result}")
            print(f"N3 raw result: {n3_result}")
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()