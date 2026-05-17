import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case


TEST_CASES = [
    {
        "name": "already lowercase",
        "input": "ahmed studies. does ahmed pass?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "mixed case sentence",
        "input": "Ahmed Studies. Does Ahmed Pass?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "uppercase sentence",
        "input": "AHMED STUDIES. DOES AHMED PASS?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "preserve punctuation",
        "input": "Ahmed studies, Sara sleeps! Does Ahmed pass?",
        "expected_success": True,
        "expected_output": "ahmed studies, sara sleeps! does ahmed pass?",
    },
    {
        "name": "preserve line breaks",
        "input": "Ahmed Studies.\nDoes Ahmed Pass?",
        "expected_success": True,
        "expected_output": "ahmed studies.\ndoes ahmed pass?",
    },
    {
        "name": "empty string",
        "input": "",
        "expected_success": True,
        "expected_output": "",
    },
    {
        "name": "none input",
        "input": None,
        "expected_success": False,
        "expected_output": None,
    },
]


def run_tests():
    passed = 0

    for case in TEST_CASES:
        print("=" * 100)
        print(f"TEST: {case['name']}")
        print("RAW INPUT:")
        print(case["input"])

        result = unify_case(case["input"])

        print("\nCASE UNIFICATION RESULT:")
        print(result)

        if result["success"] != case["expected_success"]:
            print("\nFAIL: wrong success value")
            print(f"Expected {case['expected_success']}, got {result['success']}")
            continue

        if case["expected_success"] is True:
            if result["case_unified_input"] != case["expected_output"]:
                print("\nFAIL: wrong lowercase output")
                print(f"Expected: {case['expected_output']}")
                print(f"Actual:   {result['case_unified_input']}")
                continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")


if __name__ == "__main__":
    run_tests()