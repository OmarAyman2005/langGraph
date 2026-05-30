import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from llm_response.llm_utils import generation_llm
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from prompts.llm_response_prompt import SYSTEM_PROMPT


CUMULATIVE_TEST_CASES = [
    # ==================================================
    # PARSER 1 FAILURE REGRESSION CASES
    # ==================================================
    {
        "name": "empty normalized prompt fails at parser 1",
        "normalized_input": "",
        "expected_success": False,
        "expected_stage": "parser_1",
        "expected_error_contains": "Empty normalized prompt",
    },
    {
        "name": "missing question section fails at parser 1",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies."
        ),
        "expected_success": False,
        "expected_stage": "parser_1",
        "expected_error_contains": "Missing Question section",
    },

    # ==================================================
    # PARSER 1 + LLM + PARSER 2 CASES
    # ==================================================
    {
        "name": "modus ponens entailed",
        "normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_success": True,
    },
    {
        "name": "modus tollens case may be logically invalid but should parse",
        "normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. not ahmed passes.\n"
            "\n"
            "Question:\n"
            "does ahmed not study?"
        ),
        "expected_success": True,
    },
    {
        "name": "multi-step chain",
        "normalized_input": (
            "Premises:\n"
            "1. if it rains, then the ground is wet.\n"
            "2. if the ground is wet, then the match is cancelled.\n"
            "3. it rains.\n"
            "\n"
            "Question:\n"
            "is the match cancelled?"
        ),
        "expected_success": True,
    },
    {
        "name": "conjunction elimination",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies and sara sleeps.\n"
            "\n"
            "Question:\n"
            "does sara sleep?"
        ),
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies or sara sleeps.\n"
            "2. not sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
    },
    {
        "name": "target not found special case",
        "normalized_input": (
            "Premises:\n"
            "1. if it rains, then the ground is wet.\n"
            "2. it rains.\n"
            "\n"
            "Question:\n"
            "is the sky blue?"
        ),
        "expected_success": True,
    },
    {
        "name": "not entailed because positive counterpart is derivable",
        "normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed not pass?"
        ),
        "expected_success": True,
    },
]


DIRECT_PARSER_TEST_CASES = [
    # ==================================================
    # VALID RAW LLM RESPONSES
    # ==================================================
    {
        "name": "valid single step",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": True,
        "expected_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "ahmed passes.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
    },
    {
        "name": "valid multiple steps",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: the ground is wet. [from: P1, P3] [rule: Modus Ponens]\n"
            "S2: the match is cancelled. [from: S1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": True,
        "expected_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "the ground is wet.",
                    "supports": ["P1", "P3"],
                    "rule": "Modus Ponens",
                },
                {
                    "id": "S2",
                    "statement": "the match is cancelled.",
                    "supports": ["S1", "P2"],
                    "rule": "Modus Ponens",
                },
            ],
            "special_case": None,
        },
    },
    {
        "name": "valid not entailed with derivation",
        "raw_output": (
            "Answer: not_entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": True,
        "expected_trace": {
            "answer": "not_entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "ahmed passes.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
    },
    {
        "name": "valid target not found special case",
        "raw_output": (
            "Answer: not_entailed\n"
            "Steps:\n"
            "Target Not Found in Premises"
        ),
        "expected_success": True,
        "expected_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
    },
    {
        "name": "valid from without colon tolerated",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": True,
        "expected_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "ahmed passes.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
    },

    # ==================================================
    # INVALID RAW LLM RESPONSES
    # ==================================================
    {
        "name": "empty raw output",
        "raw_output": "",
        "expected_success": False,
        "expected_error_contains": "Empty LLM output",
    },
    {
        "name": "markdown code fence rejected",
        "raw_output": (
            "```text\n"
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]\n"
            "```"
        ),
        "expected_success": False,
        "expected_error_contains": "markdown",
    },
    {
        "name": "missing answer line",
        "raw_output": (
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Answer line",
    },
    {
        "name": "invalid answer value",
        "raw_output": (
            "Answer: maybe\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Answer line",
    },
    {
        "name": "missing steps section",
        "raw_output": (
            "Answer: entailed\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Steps section",
    },
    {
        "name": "no steps after steps section",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:"
        ),
        "expected_success": False,
        "expected_error_contains": "No steps found",
    },
    {
        "name": "malformed step missing from",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Malformed step format",
    },
    {
        "name": "malformed step missing rule",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2]"
        ),
        "expected_success": False,
        "expected_error_contains": "Malformed step format",
    },
    {
        "name": "step numbering skips S1",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S2: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid step numbering",
    },
    {
        "name": "step numbering skips S2",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed studies. [from: P2] [rule: Conjunction Elimination]\n"
            "S3: ahmed passes. [from: P1, S1] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid step numbering",
    },
    {
        "name": "invalid support lowercase p1",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: p1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "Invalid support reference",
    },
    {
        "name": "step references itself",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: S1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "earlier step",
    },
    {
        "name": "step references future step",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: S2, P2] [rule: Modus Ponens]\n"
            "S2: ahmed studies. [from: P1] [rule: Conjunction Elimination]"
        ),
        "expected_success": False,
        "expected_error_contains": "earlier step",
    },
    {
        "name": "unsupported rule rejected",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Magic Rule]"
        ),
        "expected_success": False,
        "expected_error_contains": "Unsupported rule",
    },
    {
        "name": "uppercase statement rejected",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: Ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "lowercase",
    },
    {
        "name": "statement without period rejected",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "S1: ahmed passes [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "period",
    },
    {
        "name": "target not found cannot be entailed",
        "raw_output": (
            "Answer: entailed\n"
            "Steps:\n"
            "Target Not Found in Premises"
        ),
        "expected_success": False,
        "expected_error_contains": "not_entailed",
    },
    {
        "name": "target not found must appear alone",
        "raw_output": (
            "Answer: not_entailed\n"
            "Steps:\n"
            "Target Not Found in Premises\n"
            "S1: ahmed passes. [from: P1, P2] [rule: Modus Ponens]"
        ),
        "expected_success": False,
        "expected_error_contains": "must appear alone",
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def call_llm_response_generator(normalized_input: str) -> str:
    human_prompt = f"""Normalized problem:
{normalized_input}
"""

    response = generation_llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]
    )

    return response.content.strip()


def run_cumulative_tests() -> tuple[int, int]:
    print("=" * 100)
    print("CUMULATIVE TESTS: Parser 1 + LLM Response Generator + Parser 2")
    print("=" * 100)

    passed = 0
    total = len(CUMULATIVE_TEST_CASES)

    for index, case in enumerate(CUMULATIVE_TEST_CASES, start=1):
        print("=" * 100)
        print(f"CUMULATIVE TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        normalized_input = case["normalized_input"]

        print("NORMALIZED INPUT:")
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
                print(parser_1_result)

            continue

        print("\nPARSER 1: PASSED")
        print(parser_1_result["problem"])

        # ==================================================
        # LLM Response Generator
        # ==================================================
        raw_llm_output = call_llm_response_generator(normalized_input)

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
                print(parser_2_result)

            continue

        print("\nPARSER 2: PASSED")
        print("Parsed Trace:")
        print(parser_2_result["trace"])

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but pipeline passed.")

    return passed, total


def run_direct_parser_tests() -> tuple[int, int]:
    print("=" * 100)
    print("DIRECT TESTS: Parser 2 Only")
    print("=" * 100)

    passed = 0
    total = len(DIRECT_PARSER_TEST_CASES)

    for index, case in enumerate(DIRECT_PARSER_TEST_CASES, start=1):
        print("=" * 100)
        print(f"DIRECT TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        raw_output = case["raw_output"]

        print("RAW LLM OUTPUT:")
        print(raw_output)

        result = parse_llm_response(raw_output)

        if result["response_parse_success"] is False:
            print("\nPARSER 2: FAILED")
            print(result.get("response_parse_error"))

            success_ok = case["expected_success"] is False
            error_ok = contains(
                result.get("response_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(result)

            continue

        print("\nPARSER 2: PASSED")
        print("Parsed Trace:")
        print(result["trace"])

        success_ok = case["expected_success"] is True
        trace_ok = result["trace"] == case.get("expected_trace")

        if success_ok and trace_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected trace:")
            print(case.get("expected_trace"))
            print("Actual trace:")
            print(result["trace"])

    return passed, total


def main() -> None:
    cumulative_passed, cumulative_total = run_cumulative_tests()
    direct_passed, direct_total = run_direct_parser_tests()

    total_passed = cumulative_passed + direct_passed
    total = cumulative_total + direct_total

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {total_passed}/{total}")
    print(f"- Cumulative: {cumulative_passed}/{cumulative_total}")
    print(f"- Direct Parser 2: {direct_passed}/{direct_total}")

    if total_passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()