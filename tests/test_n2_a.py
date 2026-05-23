import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question


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
    # VALID N2 CASES — one proper yes/no question
    # ==================================================
    {
        "name": "valid does-question at end",
        "input": "Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies.",
    },
    {
        "name": "valid is-question at end",
        "input": "The ground is wet. Is the ground wet?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "is the ground wet?",
        "expected_candidate": "the ground is wet.",
    },
    {
        "name": "valid will-question at end",
        "input": "Ahmed studies. Will Ahmed pass?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "will ahmed pass?",
        "expected_candidate": "ahmed studies.",
    },
    {
        "name": "valid can-question at end",
        "input": "The machine is ready. Can the machine start?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "can the machine start?",
        "expected_candidate": "the machine is ready.",
    },
    {
        "name": "valid has-question at end",
        "input": "Ahmed trains. Has Ahmed won?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "has ahmed won?",
        "expected_candidate": "ahmed trains.",
    },
    {
        "name": "valid question at beginning",
        "input": "Is Ahmed happy? Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "is ahmed happy?",
        "expected_candidate": "sara sleeps.",
    },
    {
        "name": "valid question in middle",
        "input": "Ahmed studies. Does Ahmed pass? Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies. sara sleeps.",
    },
    {
        "name": "valid question after newline",
        "input": "Ahmed studies.\nDoes Ahmed pass?",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies.",
    },
    {
        "name": "valid question with extra spaces",
        "input": "Ahmed studies.     Does Ahmed pass?   ",
        "expected_stage": "N2",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_candidate": "ahmed studies.",
    },

    # ==================================================
    # N2 FAILURE — no question mark
    # ==================================================
    {
        "name": "no question mark with declaratives only",
        "input": "Ahmed studies. Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "yes/no-looking text without question mark",
        "input": "Ahmed studies. Does Ahmed pass",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "wh-looking text without question mark",
        "input": "Ahmed studies. What does Ahmed do",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },

    # ==================================================
    # N2 FAILURE — more than one proper yes/no question
    # ==================================================
    {
        "name": "two yes/no questions",
        "input": "Ahmed studies. Does Ahmed pass? Is Ahmed happy?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },

    # ==================================================
    # N2 FAILURE — non yes/no questions
    # ==================================================
    {
        "name": "wh question with question mark",
        "input": "Ahmed studies. What does Ahmed do?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "malformed auxiliary question missing predicate",
        "input": "Ahmed studies. Does Ahmed?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "malformed be-question missing predicate",
        "input": "Ahmed studies. Is Ahmed?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "malformed question missing subject",
        "input": "Ahmed studies. Is good?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "malformed be-question with internal be verb",
        "input": "Ahmed studies. Is Ahmed Sara is great?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },

    # ==================================================
    # MIXED QUESTION CASES
    # ==================================================
    {
        "name": "one wh question and one yes-no question",
        "input": "Ahmed studies. What does Ahmed do? Does Ahmed pass?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "one yes-no question and one malformed question",
        "input": "Ahmed studies. Does Ahmed pass? Is Ahmed?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
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
        print("SUCCESS at N2")
        print(f"Question: {case.get('expected_question')}")
        print(f"Candidate Premises: {case.get('expected_candidate')}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(stage: str, question: str | None, candidate: str | None) -> None:
    print("\nActual:")
    print(f"SUCCESS at {stage}")
    if question is not None:
        print(f"Question: {question}")
    if candidate is not None:
        print(f"Candidate Premises: {candidate}")


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

        actual_question = n2_result.get("question")
        actual_candidate = n2_result.get("candidate_premise_text")

        print_actual_success("N2", actual_question, actual_candidate)

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        candidate_ok = actual_candidate == case.get("expected_candidate")

        if success_ok and question_ok and candidate_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"N1 output: {n1_result.get('case_unified_input')}")
            print(f"N2 raw result: {n2_result}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()