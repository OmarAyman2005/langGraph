import re
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from llm_response.llm_utils import generation_llm
from parsers.normalized_prompt_parser import parse_normalized_prompt
from llm_response.llm_response_prompt import SYSTEM_PROMPT


TEST_CASES = [
    # ==================================================
    # PARSER 1 FAILURE REGRESSION CASES
    # ==================================================
    {
        "name": "empty normalized prompt fails at parser 1",
        "normalized_input": "",
        "expected_stage": "parser_1",
        "expected_success": False,
        "expected_error_contains": "Empty normalized prompt",
    },
    {
        "name": "missing question section fails at parser 1",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies."
        ),
        "expected_stage": "parser_1",
        "expected_success": False,
        "expected_error_contains": "Missing Question section",
    },
    {
        "name": "invalid premise numbering fails at parser 1",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "3. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_stage": "parser_1",
        "expected_success": False,
        "expected_error_contains": "Invalid premise numbering",
    },
    {
        "name": "unsupported premise fails at parser 1",
        "normalized_input": (
            "Premises:\n"
            "1. all cats are animals.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_stage": "parser_1",
        "expected_success": False,
        "expected_error_contains": "Premise is not in a normalized recoverable form",
    },

    # ==================================================
    # VALID PARSER 1 + LLM RESPONSE GENERATOR CASES
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
        "name": "modus tollens entailed",
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
        "name": "hypothetical syllogism case",
        "normalized_input": (
            "Premises:\n"
            "1. if it rains, then the ground is wet.\n"
            "2. if the ground is wet, then the match is cancelled.\n"
            "\n"
            "Question:\n"
            "is the match cancelled?"
        ),
        "expected_success": True,
    },
    {
        "name": "conjunction elimination entailed",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies and sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism entailed",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies or sara sleeps.\n"
            "2. not ahmed studies.\n"
            "\n"
            "Question:\n"
            "does sara sleep?"
        ),
        "expected_success": True,
    },
    {
        "name": "target not found not entailed",
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
        "name": "direct fact case",
        "normalized_input": (
            "Premises:\n"
            "1. the door is open.\n"
            "\n"
            "Question:\n"
            "is the door open?"
        ),
        "expected_success": True,
    },
]


ALLOWED_RULES = {
    "Modus Ponens",
    "Modus Tollens",
    "Hypothetical Syllogism",
    "Disjunctive Syllogism",
    "Conjunction Introduction",
    "Conjunction Elimination",
}

ANSWER_LINES = {
    "Answer: entailed",
    "Answer: not_entailed",
}


STEP_PATTERN = re.compile(
    r"^(S\d+):\s+(.+?)\s+\[from:\s+([^\]]+)\]\s+\[rule:\s+([^\]]+)\]$"
)


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


def validate_raw_llm_output(raw_output: str) -> tuple[bool, str | None]:
    """
    Validates only the format-level contract of the LLM response generator.

    Logical correctness is intentionally left for:
    Parser 2 -> Translator -> Verifier
    """

    if not isinstance(raw_output, str) or not raw_output.strip():
        return False, "LLM output is empty."

    if "```" in raw_output:
        return False, "LLM output must not contain markdown/code fences."

    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]

    if len(lines) < 3:
        return False, "LLM output must contain at least Answer line, Steps line, and one step/special case."

    if lines[0] not in ANSWER_LINES:
        return False, "First line must be exactly 'Answer: entailed' or 'Answer: not_entailed'."

    if lines[1] != "Steps:":
        return False, "Second line must be exactly 'Steps:'."

    step_lines = lines[2:]

    # Special target-not-found format.
    if len(step_lines) == 1 and step_lines[0] == "Target Not Found in Premises":
        if lines[0] != "Answer: not_entailed":
            return False, "Target Not Found case must use Answer: not_entailed."
        return True, None

    expected_step_number = 1

    for line in step_lines:
        match = STEP_PATTERN.match(line)

        if not match:
            return False, f"Malformed step line: {line}"

        step_id = match.group(1)
        statement = match.group(2).strip()
        supports_raw = match.group(3).strip()
        rule = match.group(4).strip()

        expected_step_id = f"S{expected_step_number}"

        if step_id != expected_step_id:
            return False, f"Invalid step numbering: expected {expected_step_id}, got {step_id}."

        if not statement:
            return False, f"Empty statement in {step_id}."

        if not statement.endswith("."):
            return False, f"Statement in {step_id} must end with a period."

        if statement != statement.lower():
            return False, f"Statement in {step_id} must be lowercase."

        supports = [support.strip() for support in supports_raw.split(",") if support.strip()]

        if not supports:
            return False, f"No supports found in {step_id}."

        for support in supports:
            if not re.match(r"^(P\d+|S\d+)$", support):
                return False, f"Invalid support ID in {step_id}: {support}"

            if support.startswith("S"):
                support_number = int(support[1:])
                if support_number >= expected_step_number:
                    return False, f"{step_id} cannot depend on itself or a later step: {support}"

        if rule not in ALLOWED_RULES:
            return False, f"Unsupported rule name in {step_id}: {rule}"

        expected_step_number += 1

    return True, None


def print_test_header(index: int, total: int, name: str) -> None:
    print("=" * 100)
    print(f"TEST {index}/{total}: {name}")
    print("-" * 100)


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: Parser 1 + LLM Response Generator")
    print("Input assumption: examples are already normalized outputs from the Normalizer.")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

        normalized_input = case["normalized_input"]

        print("NORMALIZED INPUT:")
        print(normalized_input)

        # ==================================================
        # Parser 1
        # ==================================================
        parser_result = parse_normalized_prompt(normalized_input)

        if parser_result["prompt_parse_success"] is False:
            print("\nPARSER 1: FAILED")
            print(parser_result.get("prompt_parse_error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "parser_1"
            error_ok = contains(
                parser_result.get("prompt_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nParser Result:")
                print(parser_result)

            continue

        print("\nPARSER 1: PASSED")
        print("Parsed Problem:")
        print(parser_result["problem"])

        # ==================================================
        # LLM Response Generator
        # ==================================================
        raw_llm_output = call_llm_response_generator(normalized_input)

        print("\nRAW LLM OUTPUT:")
        print(raw_llm_output)

        valid_format, format_error = validate_raw_llm_output(raw_llm_output)

        if not valid_format:
            print("\nLLM OUTPUT FORMAT: FAILED")
            print(format_error)

            print("\nResult: FAIL")
            print("\nRaw Output:")
            print(raw_llm_output)
            continue

        print("\nLLM OUTPUT FORMAT: PASSED")

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure, but Parser 1 and LLM generation both passed.")

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()