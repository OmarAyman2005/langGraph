import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.sentence_pattern_matcher import match_sentence_patterns


TEST_CASES = [
    # Already supported patterns
    {
        "name": "already facts",
        "premises": ["ahmed studies", "sara sleeps"],
        "expected_success": True,
        "expected_premises": ["ahmed studies", "sara sleeps"],
    },
    {
        "name": "already conditional",
        "premises": ["if ahmed studies ahmed passes", "ahmed studies"],
        "expected_success": True,
        "expected_premises": ["if ahmed studies then ahmed passes", "ahmed studies"],
    },
    {
        "name": "already conjunction",
        "premises": ["ahmed studies and sara sleeps"],
        "expected_success": True,
        "expected_premises": ["ahmed studies and sara sleeps"],
    },
    {
        "name": "already disjunction",
        "premises": ["ahmed studies or sara sleeps"],
        "expected_success": True,
        "expected_premises": ["ahmed studies or sara sleeps"],
    },
    {
        "name": "already negation",
        "premises": ["not ahmed studies"],
        "expected_success": True,
        "expected_premises": ["not ahmed studies"],
    },

    # Safely rewritable
    {
        "name": "x if y rewrite",
        "premises": ["ahmed passes if ahmed studies"],
        "expected_success": True,
        "expected_premises": ["if ahmed studies then ahmed passes"],
    },
    {
        "name": "only-if rewrite",
        "premises": ["ahmed passes only if ahmed studies"],
        "expected_success": True,
        "expected_premises": ["if ahmed passes then ahmed studies"],
    },
    {
        "name": "both conjunction rewrite",
        "premises": ["both ahmed studies and sara sleeps"],
        "expected_success": True,
        "expected_premises": ["ahmed studies and sara sleeps"],
    },
    {
        "name": "either disjunction rewrite",
        "premises": ["either ahmed studies or sara sleeps"],
        "expected_success": True,
        "expected_premises": ["ahmed studies or sara sleeps"],
    },
    {
        "name": "explicit negation rewrites",
        "premises": [
            "ahmed is not good",
            "sara does not study",
            "it is false that talaat wins",
        ],
        "expected_success": True,
        "expected_premises": [
            "not ahmed is good",
            "not sara studies",
            "not talaat wins",
        ],
    },

    # Valid facts
    {
        "name": "negative meaning words remain facts",
        "premises": ["ahmed fails", "sara is bad", "the ground is dry"],
        "expected_success": True,
        "expected_premises": ["ahmed fails", "sara is bad", "the ground is dry"],
    },
    {
        "name": "pronoun and simple property facts",
        "premises": ["he studies", "it rains", "the sensor is active"],
        "expected_success": True,
        "expected_premises": ["he studies", "it rains", "the sensor is active"],
    },

    # Invalid / unsupported
    {
        "name": "quantifiers rejected",
        "premises": ["all mammals are animals", "some students study"],
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "comparison and compound subject rejected",
        "premises": ["ahmed is taller than sara", "ahmed and sara study"],
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "imperative rejected",
        "premises": ["go home"],
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "uncertainty rejected",
        "premises": ["ahmed might study", "sara probably passes"],
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
    "name": "modal negation rewrite",
    "premises": ["they won't play", "ahmed cannot swim"],
    "expected_success": True,
    "expected_premises": ["not they will play", "not ahmed can swim"],
    },
]


def normalize_list(items):
    return [item.strip().lower() for item in items]


def contains_expected(actual_list, expected_list):
    actual = normalize_list(actual_list)
    expected = normalize_list(expected_list)
    return all(exp in actual for exp in expected)


def run_tests():
    passed = 0

    for case in TEST_CASES:
        print("=" * 100)
        print(f"TEST: {case['name']}")
        print("INPUT PREMISES:")
        print(case["premises"])

        print("\n" + "-" * 100)
        print("N4: SENTENCE PATTERN MATCH")
        n4 = match_sentence_patterns(case["premises"])
        print(n4)

        expected_success = case["expected_success"]

        if n4["success"] != expected_success:
            print("\nFAIL: wrong N4 success value")
            print(f"Expected: {expected_success}")
            print(f"Actual:   {n4['success']}")
            continue

        if expected_success:
            expected_premises = case.get("expected_premises", [])

            if not contains_expected(n4["pattern_matched_premises"], expected_premises):
                print("\nFAIL: pattern matched premise mismatch")
                print(f"Expected to contain: {expected_premises}")
                print(f"Actual: {n4['pattern_matched_premises']}")
                continue

        else:
            expected_error = case.get("expected_error_contains", "")

            if expected_error.lower() not in n4.get("error", "").lower():
                print("\nFAIL: error mismatch")
                print(f"Expected error containing: {expected_error}")
                print(f"Actual error: {n4.get('error')}")
                continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")


if __name__ == "__main__":
    run_tests()