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


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def read_multiline_input() -> str:
    print("Manual Test: Full Normalizer + Parser 1 + LLM Response Generator")
    print("Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 → Parser 1 → LLM Response")
    print("Paste one raw input.")
    print("When finished, type END on a new line.")
    print("=" * 100)

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines)


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


def print_normalizer_debug(normalizer_result: dict) -> None:
    debug = normalizer_result.get("debug", {})

    if not debug:
        return

    print("\n" + "-" * 100)
    print("NORMALIZER DEBUG SUMMARY")

    if "normalized_prompt_after_n6" in debug:
        print("\nNormalized Prompt After N6:")
        print(debug["normalized_prompt_after_n6"])

    if "normalized_prompt_after_n7" in debug:
        print("\nNormalized Prompt After N7:")
        print(debug["normalized_prompt_after_n7"])

    if "final_normalized_prompt_after_n8" in debug:
        print("\nFinal Normalized Prompt After N8:")
        print(debug["final_normalized_prompt_after_n8"])

    n7_result = debug.get("n7_synonym_words_unifier")
    if n7_result is not None:
        print("\nN7 Synonym Change(s):")
        changes = n7_result.get("changes", [])
        if changes:
            print(pretty_json(changes))
        else:
            print("- None")

    n8_result = debug.get("n8_antonym_words_unifier")
    if n8_result is not None:
        print("\nN8 Antonym Change(s):")
        changes = n8_result.get("changes", [])
        if changes:
            print(pretty_json(changes))
        else:
            print("- None")


def main() -> None:
    raw_input = read_multiline_input()

    print("\n" + "=" * 100)
    print("RAW INPUT:")
    print(raw_input)

    # ==================================================
    # Full Normalizer
    # ==================================================
    print("\n" + "-" * 100)
    print("FULL NORMALIZER — N1 TO N8")

    normalizer_result = normalize_raw_prompt(raw_input)

    if normalizer_result["success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(normalizer_result.get("error"))

        print("\nFull Normalizer Result:")
        print(pretty_json(normalizer_result))

        print("\nFinal Result: FAILED at Normalizer")
        return

    print("Status: PASSED")

    print_normalizer_debug(normalizer_result)

    normalized_input = normalizer_result["normalized_input"]

    print("\n" + "-" * 100)
    print("FINAL NORMALIZED INPUT:")
    print(normalized_input)

    # ==================================================
    # Parser 1
    # ==================================================
    print("\n" + "-" * 100)
    print("PARSER 1 — NORMALIZED PROMPT PARSER")

    parser_1_result = parse_normalized_prompt(normalized_input)

    if parser_1_result["prompt_parse_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(parser_1_result.get("prompt_parse_error"))

        print("\nFull Parser 1 Result:")
        print(pretty_json(parser_1_result))

        print("\nFinal Result: FAILED at Parser 1")
        return

    print("Status: PASSED")

    print("\nParsed Problem Object:")
    print(pretty_json(parser_1_result["problem"]))

    # ==================================================
    # LLM Response Generator
    # ==================================================
    print("\n" + "-" * 100)
    print("LLM RESPONSE GENERATOR")

    raw_llm_output = call_llm_response_generator(normalized_input)

    print("Status: GENERATED")

    print("\nRaw LLM Output:")
    print(raw_llm_output)

    # ==================================================
    # Format Validation
    # ==================================================
    print("\n" + "-" * 100)
    print("LLM OUTPUT FORMAT CHECK")

    valid_format, format_error = validate_raw_llm_output(raw_llm_output)

    if not valid_format:
        print("Status: FAILED")
        print("Error:")
        print(format_error)

        print("\nFinal Result: FAILED at LLM Response Format Check")
        return

    print("Status: PASSED")
    print("\nFinal Result: PASSED Full Normalizer + Parser 1 + LLM Response Generator")


if __name__ == "__main__":
    main()