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
    # N3 FAILURE CASE
    # ==================================================
    {
        "name": "question only fails at N3",
        "input": "Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },

    # ==================================================
    # N4 FAILURE CASE
    # ==================================================
    {
        "name": "unsupported premise fails at N4",
        "input": "All cats are animals. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },

    # ==================================================
    # VALID N5 QUESTION TARGETS
    # ==================================================
    {
        "name": "valid be-question target",
        "input": "Ahmed studies. Is Ahmed happy?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "is ahmed happy?",
        "expected_premises": ["ahmed studies."],
        "expected_target_candidates": ["ahmed is happy."],
    },
    {
        "name": "valid be-question with article complement",
        "input": "Ahmed studies. Is Ahmed a student?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "is ahmed a student?",
        "expected_premises": ["ahmed studies."],
        "expected_target_candidates": ["ahmed is a student."],
    },
    {
        "name": "valid be-question with determiner subject",
        "input": "The sensor is active. Is the sensor active?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "is the sensor active?",
        "expected_premises": ["the sensor is active."],
        "expected_target_candidates": ["the sensor is active."],
    },
    {
        "name": "valid negative be-question target",
        "input": "Ahmed studies. Is Ahmed not happy?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "is ahmed not happy?",
        "expected_premises": ["ahmed studies."],
        "expected_target_candidates": ["not ahmed is happy."],
    },
    {
        "name": "valid does-question target",
        "input": "Ahmed studies. Does Ahmed study?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "does ahmed study?",
        "expected_premises": ["ahmed studies."],
        "expected_target_candidates": [
            "ahmed studies.",
            "ahmed does study.",
        ],
    },
    {
        "name": "valid do-question target",
        "input": "They play. Do they play?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "do they play?",
        "expected_premises": ["they play."],
        "expected_target_candidates": [
            "they play.",
            "they do play.",
        ],
    },
    {
        "name": "valid did-question target",
        "input": "Ahmed studied. Did Ahmed study?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "did ahmed study?",
        "expected_premises": ["ahmed studied."],
        "expected_target_candidates": ["ahmed did study."],
    },
    {
        "name": "valid modal-question target",
        "input": "Ahmed swims. Can Ahmed swim?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "can ahmed swim?",
        "expected_premises": ["ahmed swims."],
        "expected_target_candidates": ["ahmed can swim."],
    },
    {
        "name": "valid has-question target",
        "input": "Ahmed trains. Has Ahmed won?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "has ahmed won?",
        "expected_premises": ["ahmed trains."],
        "expected_target_candidates": ["ahmed has won."],
    },
    {
        "name": "valid phrasal verb question target",
        "input": "The guard sleeps. Does the guard wake up?",
        "expected_stage": "N5",
        "expected_success": True,
        "expected_question": "does the guard wake up?",
        "expected_premises": ["the guard sleeps."],
        "expected_target_candidates": [
            "the guard wakes up.",
            "the guard does wake up.",
        ],
    },

    # ==================================================
    # INVALID N5 QUESTION TARGETS
    # ==================================================
    {
        "name": "question target with comparison rejected",
        "input": "Ahmed studies. Is Ahmed taller than Sara?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },
    {
        "name": "question target with quantifier rejected",
        "input": "Ahmed studies. Are all cats animals?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },
    {
        "name": "question target with uncertainty rejected",
        "input": "Ahmed studies. Might Ahmed win?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },
    {
        "name": "question target with conjunction rejected",
        "input": "Ahmed studies. Is Ahmed happy and Sara calm?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },
    {
        "name": "question target with disjunction rejected",
        "input": "Ahmed studies. Is Ahmed happy or Sara calm?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
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
        print("SUCCESS at N5")
        print(f"Question: {case.get('expected_question')}")
        print("Pattern-Matched Premises:")
        for premise in case.get("expected_premises", []):
            print(f"- {premise}")
        print("Target Candidate(s):")
        for candidate in case.get("expected_target_candidates", []):
            print(f"- {candidate}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(
    question: str,
    premises: list[str],
    target_candidates: list[str],
    normalized_input: str,
) -> None:
    print("\nActual:")
    print("SUCCESS at N5")
    print(f"Question: {question}")
    print("Pattern-Matched Premises:")
    for premise in premises:
        print(f"- {premise}")
    print("Target Candidate(s):")
    for candidate in target_candidates:
        print(f"- {candidate}")
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

        # -------------------------------
        # N4
        # -------------------------------
        n4_result = match_sentence_patterns(n3_result["premises"])

        if n4_result["success"] is False:
            actual_stage = "N4"
            actual_error = n4_result.get("error")

            print_actual_failure(actual_stage, actual_error)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N4"
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
                print(f"N4 raw result: {n4_result}")
            continue

        # -------------------------------
        # N5
        # -------------------------------
        n5_result = validate_question_pattern(n2_result["question"])

        if n5_result["success"] is False:
            actual_stage = "N5"
            actual_error = n5_result.get("error")

            print_actual_failure(actual_stage, actual_error)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N5"
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
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
            continue

        actual_question = n2_result["question"]
        actual_premises = n4_result["pattern_matched_premises"]
        actual_targets = n5_result["target_candidates"]

        actual_normalized_input = build_normalized_prompt(
            premises=actual_premises,
            question=actual_question,
        )

        print_actual_success(
            actual_question,
            actual_premises,
            actual_targets,
            actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")
        targets_ok = actual_targets == case.get("expected_target_candidates")

        if success_ok and question_ok and premises_ok and targets_ok:
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
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()