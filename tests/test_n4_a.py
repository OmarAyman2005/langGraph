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
        "name": "question only fails at N3",
        "input": "Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },

    # ==================================================
    # VALID N4 — already supported patterns
    # ==================================================
    {
        "name": "fact premises",
        "input": "Ahmed studies. Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
        ],
    },
    {
        "name": "already conditional",
        "input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "conditional missing comma before then",
        "input": "If Ahmed studies then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "if x comma y rewrite",
        "input": "If Ahmed studies, Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "already negation with not",
        "input": "Not Ahmed studies. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed studies.",
            "sara sleeps.",
        ],
    },
    {
        "name": "already conjunction",
        "input": "Ahmed studies and Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
    },
    {
        "name": "already disjunction",
        "input": "Ahmed studies or Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies or sara sleeps.",
        ],
    },

    # ==================================================
    # VALID N4 — safe conditional rewrites
    # ==================================================
    {
        "name": "y if x rewrite",
        "input": "Ahmed passes if Ahmed studies. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "y only if x rewrite",
        "input": "Ahmed passes only if Ahmed studies. Ahmed passes. Does Ahmed study?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed study?",
        "expected_premises": [
            "if ahmed passes, then ahmed studies.",
            "ahmed passes.",
        ],
    },
    {
        "name": "x implies y rewrite",
        "input": "Ahmed studies implies Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },

    # ==================================================
    # VALID N4 — safe negation rewrites
    # ==================================================
    {
        "name": "be negation rewrite",
        "input": "Ahmed is not happy. Sara sleeps. Is Sara asleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "is sara asleep?",
        "expected_premises": [
            "not ahmed is happy.",
            "sara sleeps.",
        ],
    },
    {
        "name": "does not rewrite",
        "input": "Sara does not study. Ahmed sleeps. Does Ahmed sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed sleep?",
        "expected_premises": [
            "not sara studies.",
            "ahmed sleeps.",
        ],
    },
    {
        "name": "do not rewrite",
        "input": "They do not play. Ahmed sleeps. Does Ahmed sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed sleep?",
        "expected_premises": [
            "not they play.",
            "ahmed sleeps.",
        ],
    },
    {
        "name": "did not rewrite",
        "input": "Ahmed did not study. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed did study.",
            "sara sleeps.",
        ],
    },
    {
        "name": "will not rewrite",
        "input": "Ahmed will not travel. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed will travel.",
            "sara sleeps.",
        ],
    },
    {
        "name": "cannot rewrite",
        "input": "Ahmed cannot swim. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed can swim.",
            "sara sleeps.",
        ],
    },
    {
        "name": "explicit falsehood rewrite",
        "input": "It is false that Ahmed studies. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed studies.",
            "sara sleeps.",
        ],
    },
    {
        "name": "not true rewrite",
        "input": "It is not true that Ahmed studies. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "not ahmed studies.",
            "sara sleeps.",
        ],
    },

    # ==================================================
    # VALID N4 — conjunction/disjunction rewrites
    # ==================================================
    {
        "name": "both x and y rewrite",
        "input": "Both Ahmed studies and Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
    },
    {
        "name": "x as well as y rewrite",
        "input": "Ahmed studies as well as Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
    },
    {
        "name": "x and also y rewrite",
        "input": "Ahmed studies and also Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
    },
    {
        "name": "either x or y rewrite",
        "input": "Either Ahmed studies or Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies or sara sleeps.",
        ],
    },
    {
        "name": "x or else y rewrite",
        "input": "Ahmed studies or else Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies or sara sleeps.",
        ],
    },

    # ==================================================
    # N4 FAILURE CASES
    # ==================================================
    {
        "name": "quantifier rejected",
        "input": "All cats are animals. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["all cats are animals."],
    },
    {
        "name": "comparison rejected",
        "input": "Ahmed is taller than Sara. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["ahmed is taller than sara."],
    },
    {
        "name": "uncertainty rejected",
        "input": "Ahmed probably studies. Sara sleeps. Does Sara sleep?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["ahmed probably studies."],
    },
    {
        "name": "compound subject rejected",
        "input": "Ahmed and Sara study. Omar sleeps. Does Omar sleep?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["ahmed and sara study."],
    },
    {
        "name": "because rejected",
        "input": "Ahmed passes because Ahmed studies. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["ahmed passes because ahmed studies."],
    },
    {
        "name": "unless rejected",
        "input": "Ahmed passes unless Ahmed sleeps. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
        "expected_failed_premises": ["ahmed passes unless ahmed sleeps."],
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
        print("SUCCESS at N4")
        print(f"Question: {case.get('expected_question')}")
        print("Pattern-Matched Premises:")
        for premise in case.get("expected_premises", []):
            print(f"- {premise}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")
        if case.get("expected_failed_premises"):
            print("Expected Failed Premises:")
            for premise in case["expected_failed_premises"]:
                print(f"- {premise}")


def print_actual_success(question: str, pattern_premises: list[str], normalized_input: str) -> None:
    print("\nActual:")
    print("SUCCESS at N4")
    print(f"Question: {question}")
    print("Pattern-Matched Premises:")
    for premise in pattern_premises:
        print(f"- {premise}")
    print("Normalized Input:")
    print(normalized_input)


def print_actual_failure(stage: str, error: str | None, failed_premises: list[str] | None = None) -> None:
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
            failed_premises = n4_result.get("failed_premises", [])

            print_actual_failure(actual_stage, actual_error, failed_premises)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N4"
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            expected_failed = case.get("expected_failed_premises")
            failed_ok = True
            if expected_failed is not None:
                failed_ok = failed_premises == expected_failed

            if success_ok and stage_ok and error_ok and failed_ok:
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

        actual_question = n2_result["question"]
        actual_premises = n4_result["pattern_matched_premises"]

        actual_normalized_input = build_normalized_prompt(
            premises=actual_premises,
            question=actual_question,
        )

        print_actual_success(
            actual_question,
            actual_premises,
            actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")

        if success_ok and question_ok and premises_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"N1 output: {n1_result.get('case_unified_input')}")
            print(f"N2 raw result: {n2_result}")
            print(f"N3 raw result: {n3_result}")
            print(f"N4 raw result: {n4_result}")
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()