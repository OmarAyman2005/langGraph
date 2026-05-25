import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case


"""
Automated cumulative test for Normalizer Component N1: Character Adjuster / Case Unifier.

N1 expected functionality:
1. Reject empty input.
2. Reject non-English / non-ASCII characters.
3. Reject unsupported ASCII symbols.
4. Allow English letters, digits, whitespace, and supported punctuation.
5. Convert valid English input to lowercase without changing punctuation/spacing.
"""


TEST_CASES = [
    # ==================================================
    # VALID CASES — lowercase/case conversion
    # ==================================================
    {
        "name": "already lowercase input stays the same",
        "input": "ahmed studies. does ahmed pass?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "mixed case input becomes lowercase",
        "input": "Ahmed Studies. Does Ahmed Pass?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "uppercase input becomes lowercase",
        "input": "AHMED STUDIES. DOES AHMED PASS?",
        "expected_success": True,
        "expected_output": "ahmed studies. does ahmed pass?",
    },
    {
        "name": "proper names become lowercase",
        "input": "Sara Sleeps. Does Sara Dream?",
        "expected_success": True,
        "expected_output": "sara sleeps. does sara dream?",
    },

    # ==================================================
    # VALID CASES — supported punctuation
    # ==================================================
    {
        "name": "supported punctuation comma exclamation semicolon colon",
        "input": "Ahmed studies, Sara sleeps! Does Ahmed pass; or fail: maybe?",
        "expected_success": True,
        "expected_output": "ahmed studies, sara sleeps! does ahmed pass; or fail: maybe?",
    },
    {
        "name": "apostrophe rejected",
        "input": "Ahmed doesn't study. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: '",
    },
    {
        "name": "supported parentheses and hyphen",
        "input": "Ahmed studies (today). Does Ahmed re-pass?",
        "expected_success": True,
        "expected_output": "ahmed studies (today). does ahmed re-pass?",
    },
    {
        "name": "all supported punctuation together",
        "input": "A.,?!;:\"()- Z",
        "expected_success": True,
        "expected_output": "a.,?!;:\"()- z",
    },

    # ==================================================
    # VALID CASES — whitespace and digits
    # ==================================================
    {
        "name": "preserve newlines",
        "input": "Ahmed Studies.\nDoes Ahmed Pass?",
        "expected_success": True,
        "expected_output": "ahmed studies.\ndoes ahmed pass?",
    },
    {
        "name": "preserve tabs and carriage return",
        "input": "Ahmed\tStudies.\r\nDoes\tAhmed\tPass?",
        "expected_success": True,
        "expected_output": "ahmed\tstudies.\r\ndoes\tahmed\tpass?",
    },
    {
        "name": "allow digits",
        "input": "Ahmed has 2 books. Does Ahmed have 2 books?",
        "expected_success": True,
        "expected_output": "ahmed has 2 books. does ahmed have 2 books?",
    },
    {
        "name": "valid input with leading and trailing whitespace is preserved",
        "input": "  Ahmed Studies. Does Ahmed Pass?  ",
        "expected_success": True,
        "expected_output": "  ahmed studies. does ahmed pass?  ",
    },

    # ==================================================
    # INVALID CASES — empty / invalid type
    # ==================================================
    {
        "name": "empty string rejected",
        "input": "",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "spaces only rejected",
        "input": "     ",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "newlines and tabs only rejected",
        "input": "\n\n\t\r",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "none input rejected",
        "input": None,
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "non-string input rejected",
        "input": 123,
        "expected_success": False,
        "expected_error_contains": "Input must be a string",
    },

    # ==================================================
    # INVALID CASES — non-English / non-ASCII
    # ==================================================
    {
        "name": "arabic character rejected",
        "input": "Ahmed studies أ. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: أ",
    },
    {
        "name": "accented latin character rejected",
        "input": "André studies. Does André pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: é",
    },
    {
        "name": "emoji rejected",
        "input": "Ahmed studies 😊. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊",
    },
    {
        "name": "greek character rejected",
        "input": "Ahmed studies π. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: π",
    },
    {
        "name": "en dash rejected as non-English/non-ASCII",
        "input": "Ahmed studies – Sara sleeps. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: –",
    },
    {
        "name": "multiple unique non-English characters reported once each",
        "input": "Ahmed é é studies أ أ. Does Ahmed pass 😊?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: é, أ, 😊",
    },

    # ==================================================
    # INVALID CASES — unsupported ASCII symbols
    # ==================================================
    {
        "name": "at symbol rejected",
        "input": "Ahmed studies @ school. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: @",
    },
    {
        "name": "hash and dollar rejected",
        "input": "Ahmed studies # math $ science. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: #, $",
    },
    {
        "name": "slash rejected",
        "input": "Ahmed studies math/science. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: /",
    },
    {
        "name": "underscore rejected",
        "input": "Ahmed_studies. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: _",
    },
    {
        "name": "square brackets rejected",
        "input": "Ahmed [studies]. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: [, ]",
    },
    {
        "name": "plus equals less greater rejected",
        "input": "Ahmed + Sara = success < maybe >. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: +, =, <, >",
    },

    # ==================================================
    # INVALID CASES — multiple error categories
    # ==================================================
    {
        "name": "non-English and unsupported symbol together",
        "input": "Ahmed studies 😊 @ school. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊\nUnsupported character(s) found: @",
    },
    {
        "name": "multiple non-English and multiple unsupported symbols together",
        "input": "Ahmed é studies أ @ school # today. Does Ahmed pass?",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: é, أ\nUnsupported character(s) found: @, #",
    },
]


def assert_contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return expected in actual


def run_tests() -> None:
    passed = 0

    for index, case in enumerate(TEST_CASES, start=1):
        print("=" * 100)
        print(f"TEST {index}/{len(TEST_CASES)}: {case['name']}")
        print("RAW INPUT:")
        print(repr(case["input"]))

        result = unify_case(case["input"])

        print("\nN1 RESULT:")
        print(result)

        actual_success = result.get("success")
        expected_success = case["expected_success"]

        if actual_success != expected_success:
            print("\nFAIL: wrong success value")
            print(f"Expected success={expected_success}, got success={actual_success}")
            continue

        if expected_success is True:
            expected_output = case["expected_output"]
            actual_output = result.get("case_unified_input")

            if actual_output != expected_output:
                print("\nFAIL: wrong case-unified output")
                print(f"Expected: {repr(expected_output)}")
                print(f"Actual:   {repr(actual_output)}")
                continue

            if result.get("errors") != []:
                print("\nFAIL: success result should have empty errors list")
                print(f"Actual errors: {result.get('errors')}")
                continue

            if result.get("error") is not None:
                print("\nFAIL: success result should have error=None")
                print(f"Actual error: {result.get('error')}")
                continue

            debug = result.get("debug", {})
            if debug.get("case_unified_input") != expected_output:
                print("\nFAIL: debug case_unified_input mismatch")
                print(f"Debug: {debug}")
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
            print("\nFAIL: failure result should contain a non-empty errors list")
            print(f"Actual errors: {result.get('errors')}")
            continue

        if result.get("case_unified_input") is not None:
            print("\nFAIL: failure result should have case_unified_input=None")
            print(f"Actual case_unified_input: {result.get('case_unified_input')}")
            continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")

    if passed != len(TEST_CASES):
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()