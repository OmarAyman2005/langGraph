import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from llm_response.llm_response_generator import generate_raw_llm_response


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

SPECIAL_CASE_LINES = {
    "Target Not Found in Premises",
    "No Derivation Found",
}

STEP_PATTERN = re.compile(
    r"^(S\d+):\s+(.+?)\s+\[from:\s+([^\]]+)\]\s+\[rule:\s+([^\]]+)\]$"
)


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
    # VALID RAW INPUTS — FULL NORMALIZER + PARSER 1 + LLM RESPONSE
    # Keep these mostly basic because LLM output is intentionally weak/variable.
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
        "name": "target not found not entailed",
        "raw_input": "If it rains, then the ground is wet. It rains. Is the sky blue?",
        "expected_success": True,
    },
    {
        "name": "direct fact case may be logically invalid later but should be formatted",
        "raw_input": "The door is open. Is the door open?",
        "expected_success": True,
    },
    {
        "name": "synonym unification before LLM",
        "raw_input": "Ahmed starts. Sara begins. Does Sara begin?",
        "expected_success": True,
    },
    {
        "name": "antonym unification before LLM",
        "raw_input": "The door is open. Is the door closed?",
        "expected_success": True,
    },
    {
        "name": "synonym then antonym unification before LLM",
        "raw_input": "The door is open. The window is shut. Is the window closed?",
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


def validate_raw_llm_output(raw_output: str) -> tuple[bool, str | None]:
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

    if len(step_lines) == 1 and step_lines[0] in SPECIAL_CASE_LINES:
        if lines[0] != "Answer: not_entailed":
            return False, f"{step_lines[0]} case must use Answer: not_entailed."

        return True, None

    for special_case in SPECIAL_CASE_LINES:
        if special_case in step_lines:
            return False, f"{special_case} must appear alone as the only step."

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

        supports = [
            support.strip()
            for support in supports_raw.split(",")
            if support.strip()
        ]

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
    print("Automated Test: Full Normalizer + Parser 1 + LLM Response Generator")
    print("Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 → Parser 1 → LLM Response")
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
        # LLM Output Format Check
        # ==================================================
        valid_format, format_error = validate_raw_llm_output(raw_llm_output)

        if not valid_format:
            print("\nLLM OUTPUT FORMAT CHECK: FAILED")
            print(format_error)

            if case["expected_success"] is False and case.get("expected_stage") == "llm_response":
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")

            continue

        print("\nLLM OUTPUT FORMAT CHECK: PASSED")

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but full pipeline up to LLM response passed.")

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()