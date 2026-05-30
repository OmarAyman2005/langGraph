import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.normalized_prompt_parser import parse_normalized_prompt


TEST_CASES = [
    # ==================================================
    # VALID NORMALIZED PROMPTS
    # ==================================================
    {
        "name": "single fact premise",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "two fact premises",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies.",
                "P2": "sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "conditional and fact premises",
        "normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "if ahmed studies, then ahmed passes.",
                "P2": "ahmed studies.",
            },
            "question": "does ahmed pass?",
        },
    },
    {
        "name": "negated premise",
        "normalized_input": (
            "Premises:\n"
            "1. not ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "not ahmed studies.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "conjunction premise",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies and sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies and sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "disjunction premise",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies or sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies or sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "semantic synonym normalized output",
        "normalized_input": (
            "Premises:\n"
            "1. the door is closed.\n"
            "\n"
            "Question:\n"
            "is the door closed?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "the door is closed.",
            },
            "question": "is the door closed?",
        },
    },
    {
        "name": "semantic antonym normalized output",
        "normalized_input": (
            "Premises:\n"
            "1. the door is open.\n"
            "\n"
            "Question:\n"
            "is the door not open?"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "the door is open.",
            },
            "question": "is the door not open?",
        },
    },
    {
        "name": "blank lines tolerated",
        "normalized_input": (
            "\n"
            "Premises:\n"
            "\n"
            "1. ahmed studies.\n"
            "\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "\n"
            "does ahmed study?\n"
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies.",
                "P2": "sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "extra spaces are cleaned",
        "normalized_input": (
            "Premises:\n"
            "1.   ahmed   studies.   \n"
            "2.   sara   sleeps.   \n"
            "\n"
            "Question:\n"
            "   does   ahmed   study?   "
        ),
        "expected_success": True,
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies.",
                "P2": "sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },

    # ==================================================
    # INVALID STRUCTURE CASES
    # ==================================================
    {
        "name": "empty normalized prompt",
        "normalized_input": "",
        "expected_success": False,
        "expected_error_contains": "Empty normalized prompt",
    },
    {
        "name": "missing premises section",
        "normalized_input": (
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Question section appears before Premises section",
    },
    {
        "name": "missing question section",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies."
        ),
        "expected_success": False,
        "expected_error_contains": "Missing Question section",
    },
    {
        "name": "duplicate premises section",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "Premises:\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Duplicate Premises section",
    },
    {
        "name": "duplicate question section",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?\n"
            "\n"
            "Question:\n"
            "does sara sleep?"
        ),
        "expected_success": False,
        "expected_error_contains": "Duplicate Question section",
    },
    {
        "name": "premises section after question section",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?\n"
            "\n"
            "Premises:\n"
            "2. sara sleeps."
        ),
        "expected_success": False,
        "expected_error_contains": "Premises section appears after Question section",
    },
    {
        "name": "question section before premises section",
        "normalized_input": (
            "Question:\n"
            "does ahmed study?\n"
            "\n"
            "Premises:\n"
            "1. ahmed studies."
        ),
        "expected_success": False,
        "expected_error_contains": "Question section appears before Premises section",
    },
    {
        "name": "unexpected content before sections",
        "normalized_input": (
            "hello\n"
            "\n"
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Unexpected content before sections",
    },
    {
        "name": "no premises",
        "normalized_input": (
            "Premises:\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "No premises found",
    },
    {
        "name": "missing question content",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
        ),
        "expected_success": False,
        "expected_error_contains": "Missing question content",
    },
    {
        "name": "multiple question lines",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?\n"
            "does sara sleep?"
        ),
        "expected_success": False,
        "expected_error_contains": "Multiple question lines found",
    },

    # ==================================================
    # INVALID PREMISE NUMBERING CASES
    # ==================================================
    {
        "name": "malformed premise line missing numbering dot",
        "normalized_input": (
            "Premises:\n"
            "1 ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Malformed premise line",
    },
    {
        "name": "malformed premise line missing space after dot",
        "normalized_input": (
            "Premises:\n"
            "1.ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Malformed premise line",
    },
    {
        "name": "premise numbering starts from zero",
        "normalized_input": (
            "Premises:\n"
            "0. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid premise numbering",
    },
    {
        "name": "premise numbering skips number",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "3. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid premise numbering",
    },
    {
        "name": "premise numbering repeats number",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "1. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid premise numbering",
    },
    {
        "name": "empty premise content",
        "normalized_input": (
            "Premises:\n"
            "1. \n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Malformed premise line",
    },

    # ==================================================
    # INVALID DOMAIN RECOVERABILITY CASES
    # ==================================================
    {
        "name": "unsupported quantified premise",
        "normalized_input": (
            "Premises:\n"
            "1. all cats are animals.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Premise is not in a normalized recoverable form",
    },
    {
        "name": "unsupported comparison premise",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed is taller than sara.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": False,
        "expected_error_contains": "Premise is not in a normalized recoverable form",
    },
    {
        "name": "unsupported causal premise",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed passes because ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_success": False,
        "expected_error_contains": "Premise is not in a normalized recoverable form",
    },
    {
        "name": "unsupported wh question",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "what does ahmed do?"
        ),
        "expected_success": False,
        "expected_error_contains": "Question is not in a normalized recoverable form",
    },
    {
        "name": "unsupported question with conjunction target",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "is ahmed happy and sara calm?"
        ),
        "expected_success": False,
        "expected_error_contains": "Question is not in a normalized recoverable form",
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def print_test_header(index: int, total: int, name: str) -> None:
    print("=" * 100)
    print(f"TEST {index}/{total}: {name}")
    print("-" * 100)


def print_expected(case: dict) -> None:
    print("\nExpected:")
    if case["expected_success"] is True:
        print("PARSER 1 SUCCESS")
        print("Expected Parsed Problem:")
        print(case["expected_problem"])
    else:
        print("PARSER 1 FAILURE")
        print(f"Error contains: {case.get('expected_error_contains')}")


def print_actual_success(problem: dict) -> None:
    print("\nActual:")
    print("PARSER 1 SUCCESS")
    print("Parsed Problem:")
    print(problem)


def print_actual_failure(error: str | None) -> None:
    print("\nActual:")
    print("PARSER 1 FAILURE")
    print(f"Error: {error}")


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: Parser 1 — Normalized Prompt Parser")
    print("Input assumption: examples are already normalized outputs from the Normalizer.")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

        print("NORMALIZED INPUT:")
        print(case["normalized_input"])

        print_expected(case)

        result = parse_normalized_prompt(case["normalized_input"])

        if result["prompt_parse_success"] is False:
            actual_error = result.get("prompt_parse_error")
            print_actual_failure(actual_error)

            success_ok = case["expected_success"] is False
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            if success_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(result)

            continue

        actual_problem = result["problem"]
        print_actual_success(actual_problem)

        success_ok = case["expected_success"] is True
        problem_ok = actual_problem == case.get("expected_problem")

        if success_ok and problem_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print("Expected problem:")
            print(case.get("expected_problem"))
            print("Actual problem:")
            print(actual_problem)

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()