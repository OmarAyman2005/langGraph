import re
import sys
from pathlib import Path
from pprint import pprint

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from llm_response.llm_utils import generation_llm
from parsers.normalized_prompt_parser import parse_normalized_prompt
from prompts.llm_response_prompt import SYSTEM_PROMPT


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


def read_multiline_input() -> str:
    print("Manual Test: Parser 1 + LLM Response Generator")
    print("Input assumption: paste a normalized prompt produced by the Normalizer.")
    print("Expected format:")
    print("Premises:")
    print("1. ...")
    print("2. ...")
    print()
    print("Question:")
    print("...")
    print()
    print("Paste one normalized prompt.")
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


def main() -> None:
    normalized_input = read_multiline_input()

    print("\n" + "=" * 100)
    print("NORMALIZED INPUT:")
    print(normalized_input)

    # ==================================================
    # Parser 1
    # ==================================================
    print("\n" + "-" * 100)
    print("PARSER 1 — NORMALIZED PROMPT PARSER")

    parser_result = parse_normalized_prompt(normalized_input)

    if parser_result["prompt_parse_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(parser_result.get("prompt_parse_error"))

        print("\nFull Parser Result:")
        pprint(parser_result)

        print("\nFinal Result: FAILED at Parser 1")
        return

    print("Status: PASSED")

    print("\nParsed Problem Object:")
    pprint(parser_result["problem"])

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
    print("\nFinal Result: PASSED Parser 1 + LLM Response Generator")


if __name__ == "__main__":
    main()