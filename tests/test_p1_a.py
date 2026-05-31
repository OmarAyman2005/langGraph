import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


TEST_CASES = [
    # ==================================================
    # VALID RAW INPUTS — FULL NORMALIZER + PARSER 1
    # ==================================================
    {
        "name": "single fact premise",
        "raw_input": "Ahmed studies. Does Ahmed study?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "two fact premises",
        "raw_input": "Ahmed studies. Sara sleeps. Does Ahmed study?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
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
        "raw_input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
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
        "raw_input": "Ahmed does not study. Does Ahmed study?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. not ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "not ahmed studies.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "conjunction premise",
        "raw_input": "Ahmed studies and Sara sleeps. Does Ahmed study?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies and sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies and sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "disjunction premise",
        "raw_input": "Ahmed studies or Sara sleeps. Does Ahmed study?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed studies or sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "ahmed studies or sara sleeps.",
            },
            "question": "does ahmed study?",
        },
    },
    {
        "name": "subject propagation",
        "raw_input": "Ahmed starts. He begins. Does he begin?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed starts.\n"
            "2. ahmed starts.\n"
            "\n"
            "Question:\n"
            "does ahmed start?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "ahmed starts.",
                "P2": "ahmed starts.",
            },
            "question": "does ahmed start?",
        },
    },
    {
        "name": "synonym unification with be adjective",
        "raw_input": "The box is big. The bag is large. Is the bag large?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. the box is big.\n"
            "2. the bag is big.\n"
            "\n"
            "Question:\n"
            "is the bag big?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "the box is big.",
                "P2": "the bag is big.",
            },
            "question": "is the bag big?",
        },
    },
    {
        "name": "synonym then antonym unification",
        "raw_input": "The door is open. The window is shut. Is the window closed?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. the door is open.\n"
            "2. not the window is open.\n"
            "\n"
            "Question:\n"
            "is the window not open?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "the door is open.",
                "P2": "not the window is open.",
            },
            "question": "is the window not open?",
        },
    },
    {
        "name": "antonym unification with verb",
        "raw_input": "Ahmed passes. Sara fails. Does Sara fail?",
        "expected_success": True,
        "expected_normalized_input": (
            "Premises:\n"
            "1. ahmed passes.\n"
            "2. not sara passes.\n"
            "\n"
            "Question:\n"
            "does sara not pass?"
        ),
        "expected_problem": {
            "premises": {
                "P1": "ahmed passes.",
                "P2": "not sara passes.",
            },
            "question": "does sara not pass?",
        },
    },

    # ==================================================
    # INVALID RAW INPUTS — EXPECT NORMALIZER FAILURE
    # ==================================================
    {
        "name": "empty raw input",
        "raw_input": "",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "Empty input",
    },
    {
        "name": "no question mark",
        "raw_input": "Ahmed studies. Sara sleeps.",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "question only",
        "raw_input": "Does Ahmed pass?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "unsupported quantified premise",
        "raw_input": "All cats are animals. Ahmed studies. Does Ahmed study?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "unsupported comparison premise",
        "raw_input": "Ahmed is taller than Sara. Ahmed studies. Does Ahmed study?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "unsupported wh question",
        "raw_input": "Ahmed studies. What does Ahmed do?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "unsupported conjunction target question",
        "raw_input": "Ahmed studies. Is Ahmed happy and Sara calm?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
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


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: Full Normalizer + Parser 1")
    print("Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 → Parser 1")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

        raw_input = case["raw_input"]

        print("RAW INPUT:")
        print(raw_input)

        # ==================================================
        # Full Normalizer
        # ==================================================
        normalizer_result = normalize_raw_prompt(raw_input)

        if normalizer_result["success"] is False:
            print("\nNORMALIZER: FAILED")
            print(normalizer_result.get("error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "normalizer"
            error_ok = contains(
                normalizer_result.get("error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nFull Normalizer Result:")
                print(pretty_json(normalizer_result))

            continue

        normalized_input = normalizer_result["normalized_input"]

        print("\nNORMALIZER: PASSED")
        print("\nNORMALIZED INPUT:")
        print(normalized_input)

        # ==================================================
        # Parser 1
        # ==================================================
        parser_1_result = parse_normalized_prompt(normalized_input)

        if parser_1_result["prompt_parse_success"] is False:
            print("\nPARSER 1: FAILED")
            print(parser_1_result.get("prompt_parse_error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "parser_1"
            error_ok = contains(
                parser_1_result.get("prompt_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nFull Parser 1 Result:")
                print(pretty_json(parser_1_result))

            continue

        parsed_problem = parser_1_result["problem"]

        print("\nPARSER 1: PASSED")
        print("\nParsed Problem:")
        print(pretty_json(parsed_problem))

        success_ok = case["expected_success"] is True
        normalized_ok = normalized_input == case.get("expected_normalized_input")
        problem_ok = parsed_problem == case.get("expected_problem")

        if success_ok and normalized_ok and problem_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")

            print("\nExpected Normalized Input:")
            print(case.get("expected_normalized_input"))

            print("\nActual Normalized Input:")
            print(normalized_input)

            print("\nExpected Parsed Problem:")
            print(pretty_json(case.get("expected_problem")))

            print("\nActual Parsed Problem:")
            print(pretty_json(parsed_problem))

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()