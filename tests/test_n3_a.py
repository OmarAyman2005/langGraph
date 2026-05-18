import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import segment_and_validate_premises


TEST_CASES = [
    {
        "name": "simple two premises",
        "input": "Ahmed studies. Sara sleeps. Does Ahmed pass?",
        "expected_success": True,
        "expected_premises": ["ahmed studies.", "sara sleeps."],
    },
    {
        "name": "two premises no punctuation",
        "input": "Ahmed studies Sara sleeps does Ahmed pass",
        "expected_success": True,
        "expected_premises": ["ahmed studies", "sara sleeps"],
    },
    {
        "name": "conditional plus fact with punctuation",
        "input": "If Ahmed studies, Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
        "expected_premises": ["if ahmed studies, ahmed passes.", "ahmed studies."],
    },
    {
        "name": "conditional plus fact no punctuation",
        "input": "If it rains the ground gets wet it is raining is the ground wet",
        "expected_success": True,
        "expected_premises": ["if it rains the ground gets wet", "it is raining"],
    },
    {
        "name": "question only reaches N3 no rest",
        "input": "Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "incomplete premise after question removal",
        "input": "Ahmed. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "One or more candidate premises are not complete English sentences",
    },
    {
        "name": "unfinished conditional premise",
        "input": "If Ahmed studies. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "One or more candidate premises are not complete English sentences",
    },
    {
        "name": "ambiguous segmentation",
        "input": "Ahmed knows Sara studies does Ahmed pass",
        "expected_success": False,
        "expected_error_contains": "Ambiguous premise segmentation",
    },
    {
        "name": "non ambiguous eating pizza",
        "input": "Ahmed saw Sara eating pizza does Ahmed pass",
        "expected_success": True,
        "expected_premises": ["ahmed saw sara eating pizza"],
    },
]


def contains_all(actual_list, expected_list):
    actual_joined = "\n".join(actual_list).lower()
    return all(expected.lower() in actual_joined for expected in expected_list)


def run_tests():
    passed = 0

    for case in TEST_CASES:
        print("=" * 100)
        print(f"TEST: {case['name']}")
        print("RAW INPUT:")
        print(case["input"])

        print("\n" + "-" * 100)
        print("N1: CASE UNIFICATION")
        n1 = unify_case(case["input"])
        print(n1)

        if not n1["success"]:
            print("\nFAIL: N1 failed unexpectedly")
            continue

        print("\n" + "-" * 100)
        print("N2: QUESTION DETECTION")
        n2 = detect_single_yes_no_question(n1["case_unified_input"])
        print(n2)

        if not n2["success"]:
            print("\nFAIL: N2 failed unexpectedly")
            continue

        print("\n" + "-" * 100)
        print("N3: PREMISE SEPARATION")
        n3 = segment_and_validate_premises(n2["candidate_premise_text"])
        print(n3)

        expected_success = case["expected_success"]

        if n3["success"] != expected_success:
            print("\nFAIL: wrong N3 success value")
            print(f"Expected: {expected_success}")
            print(f"Actual:   {n3['success']}")
            continue

        if expected_success:
            expected_premises = case.get("expected_premises", [])
            if not contains_all(n3["premises"], expected_premises):
                print("\nFAIL: premise mismatch")
                print(f"Expected to contain: {expected_premises}")
                print(f"Actual: {n3['premises']}")
                continue
        else:
            expected_error = case.get("expected_error_contains", "")
            if expected_error.lower() not in n3.get("error", "").lower():
                print("\nFAIL: error mismatch")
                print(f"Expected error containing: {expected_error}")
                print(f"Actual error: {n3.get('error')}")
                continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")


if __name__ == "__main__":
    run_tests()