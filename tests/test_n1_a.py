import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case


TEST_CASES = [
    # --------------------------------------------------
    # VALID CASES
    # --------------------------------------------------
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
        "name": "preserve supported punctuation",
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
        "name": "allow numbers",
        "input": "Ahmed has 2 books. Does Ahmed have 2 books?",
        "expected_success": True,
        "expected_output": "ahmed has 2 books. does ahmed have 2 books?",
    },
    {
        "name": "allow contractions with apostrophe",
        "input": "Ahmed doesn't study. Does Ahmed pass?",
        "expected_success": True,
        "expected_output": "ahmed doesn't study. does ahmed pass?",
    },
    {
        "name": "allow double quotes",
        "input": '"Ahmed studies." Does Ahmed pass?',
        "expected_success": True,
        "expected_output": '"ahmed studies." does ahmed pass?',
    },
    {
        "name": "allow parentheses and hyphen",
        "input": "Ahmed studies (today). Does Ahmed re-pass?",
        "expected_success": True,
        "expected_output": "ahmed studies (today). does ahmed re-pass?",
    },

    # --------------------------------------------------
    # INVALID EMPTY INPUT
    # --------------------------------------------------
    {
        "name": "empty string",
        "input": "",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "spaces only",
        "input": "     ",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "newlines only",
        "input": "\n\n\t",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "none input",
        "input": None,
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },

    # --------------------------------------------------
    # INVALID NON-ENGLISH CHARACTERS
    # --------------------------------------------------
    {
        "name": "arabic character",
        "input": "Ahmed studies أ. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: أ",
    },
    {
        "name": "accented latin character",
        "input": "André studies. Does André pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: é",
    },
    {
        "name": "emoji character",
        "input": "Ahmed studies 😊. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊",
    },
    {
        "name": "greek character",
        "input": "Ahmed studies π. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: π",
    },

    # --------------------------------------------------
    # INVALID UNSUPPORTED ASCII SYMBOLS
    # --------------------------------------------------
    {
        "name": "unsupported at symbol",
        "input": "Ahmed studies @ school. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: @",
    },
    {
        "name": "unsupported hash and dollar",
        "input": "Ahmed studies # math $ science. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: #, $",
    },
    {
        "name": "unsupported slash",
        "input": "Ahmed studies math/science. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: /",
    },
    {
        "name": "unsupported underscore",
        "input": "Ahmed_studies. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: _",
    },

    # --------------------------------------------------
    # MULTIPLE ERROR TYPES
    # --------------------------------------------------
    {
        "name": "non-english and unsupported symbol together",
        "input": "Ahmed studies 😊 @ school. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊\nUnsupported character(s) found: @",
    },
]


def assert_contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected in actual


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

        actual_success = result["success"]
        expected_success = case["expected_success"]

        if actual_success != expected_success:
            print("\nFAIL: wrong success value")
            print(f"Expected success={expected_success}, got success={actual_success}")
            continue

        if expected_success is True:
            expected_output = case["expected_output"]
            actual_output = result["case_unified_input"]

            if actual_output != expected_output:
                print("\nFAIL: wrong lowercase output")
                print(f"Expected: {expected_output}")
                print(f"Actual:   {actual_output}")
                continue

            if result.get("errors") != []:
                print("\nFAIL: success result should have empty errors list")
                print(f"Actual errors: {result.get('errors')}")
                continue

            print("\nPASS")
            passed += 1
            continue

        expected_error_contains = case.get("expected_error_contains")

        if not assert_contains(result.get("error"), expected_error_contains):
            print("\nFAIL: error mismatch")
            print(f"Expected error to contain: {expected_error_contains}")
            print(f"Actual error: {result.get('error')}")
            continue

        if not isinstance(result.get("errors"), list) or not result.get("errors"):
            print("\nFAIL: failure result should contain non-empty errors list")
            print(f"Actual errors: {result.get('errors')}")
            continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")


if __name__ == "__main__":
    run_tests()