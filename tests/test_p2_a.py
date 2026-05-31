import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from llm_response.llm_response_generator import generate_raw_llm_response


TEST_CASES = [
    # ==================================================
    # INVALID RAW INPUTS — EXPECT NORMALIZER FAILURE
    # ==================================================
    {
        "name": "empty raw input fails at normalizer",
        "raw_input": "",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "Empty input",
    },
    {
        "name": "missing question mark fails at normalizer",
        "raw_input": "Ahmed studies. Sara sleeps.",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "question only fails at normalizer",
        "raw_input": "Does Ahmed pass?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "unsupported premise fails at normalizer",
        "raw_input": "All cats are animals. Ahmed studies. Does Ahmed study?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },

    # ==================================================
    # VALID RAW INPUTS — FULL PIPELINE THROUGH PARSER 2
    # ==================================================
    {
        "name": "modus ponens entailed",
        "raw_input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
    },
    {
        "name": "conjunction elimination",
        "raw_input": "Ahmed studies and Sara sleeps. Does Ahmed study?",
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism",
        "raw_input": "Ahmed studies or Sara sleeps. Ahmed does not study. Does Sara sleep?",
        "expected_success": True,
    },
    {
        "name": "target not found special case",
        "raw_input": "If it rains, then the ground is wet. It rains. Is the sky blue?",
        "expected_success": True,
    },
    {
        "name": "direct fact case may be logically invalid later but should parse",
        "raw_input": "The door is open. Is the door open?",
        "expected_success": True,
    },
    {
        "name": "synonym unification before parser 2",
        "raw_input": "Ahmed starts. Sara begins. Does Sara begin?",
        "expected_success": True,
    },
    {
        "name": "antonym unification before parser 2",
        "raw_input": "The door is open. Is the door closed?",
        "expected_success": True,
    },
    {
        "name": "synonym then antonym unification before parser 2",
        "raw_input": "The door is open. The window is shut. Is the window closed?",
        "expected_success": True,
    },
    {
        "name": "verb antonym unification before parser 2",
        "raw_input": "Ahmed passes. Sara fails. Does Sara fail?",
        "expected_success": True,
    },
]


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def call_llm_response_generator(normalized_input: str) -> str:
    return generate_raw_llm_response(normalized_input)


def print_test_header(index: int, total: int, name: str) -> None:
    print("=" * 100)
    print(f"TEST {index}/{total}: {name}")
    print("-" * 100)


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: Full Normalizer + Parser 1 + LLM Response Generator + Parser 2")
    print(
        "Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 "
        "→ Parser 1 → LLM Response → Parser 2"
    )
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

        print("\nPARSER 1: PASSED")
        print("\nParsed Problem:")
        print(pretty_json(parser_1_result["problem"]))

        # ==================================================
        # LLM Response Generator
        # ==================================================
        raw_llm_output = call_llm_response_generator(normalized_input)

        print("\nLLM RESPONSE GENERATOR: GENERATED")
        print("\nRAW LLM OUTPUT:")
        print(raw_llm_output)

        # ==================================================
        # Parser 2
        # ==================================================
        parser_2_result = parse_llm_response(raw_llm_output)

        if parser_2_result["response_parse_success"] is False:
            print("\nPARSER 2: FAILED")
            print(parser_2_result.get("response_parse_error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "parser_2"
            error_ok = contains(
                parser_2_result.get("response_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nFull Parser 2 Result:")
                print(pretty_json(parser_2_result))

            continue

        parsed_trace = parser_2_result["trace"]

        print("\nPARSER 2: PASSED")
        print("\nParsed Trace:")
        print(pretty_json(parsed_trace))

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but full pipeline through Parser 2 passed.")

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()