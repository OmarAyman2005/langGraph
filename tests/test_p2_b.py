import sys
from pathlib import Path
from pprint import pprint

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from llm_response.llm_utils import generation_llm
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from prompts.llm_response_prompt import SYSTEM_PROMPT


def read_multiline_input() -> str:
    print("Manual Test: Parser 1 + LLM Response Generator + Parser 2")
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

    parser_1_result = parse_normalized_prompt(normalized_input)

    if parser_1_result["prompt_parse_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(parser_1_result.get("prompt_parse_error"))

        print("\nFull Parser 1 Result:")
        pprint(parser_1_result)

        print("\nFinal Result: FAILED at Parser 1")
        return

    print("Status: PASSED")
    print("\nParsed Problem:")
    pprint(parser_1_result["problem"])

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
    # Parser 2
    # ==================================================
    print("\n" + "-" * 100)
    print("PARSER 2 — LLM RESPONSE PARSER")

    parser_2_result = parse_llm_response(raw_llm_output)

    if parser_2_result["response_parse_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(parser_2_result.get("response_parse_error"))

        print("\nFull Parser 2 Result:")
        pprint(parser_2_result)

        print("\nFinal Result: FAILED at Parser 2")
        return

    print("Status: PASSED")

    print("\nParsed Trace Object:")
    pprint(parser_2_result["trace"])

    trace = parser_2_result["trace"]

    print("\nAnswer:")
    print(trace["answer"])

    print("\nSpecial Case:")
    print(trace["special_case"])

    print("\nSteps:")
    if trace["steps"]:
        for step in trace["steps"]:
            print(
                f"{step['id']}: {step['statement']} "
                f"[from: {', '.join(step['supports'])}] "
                f"[rule: {step['rule']}]"
            )
    else:
        print("- None")

    print("\nFinal Result: PASSED Parser 1 + LLM Response Generator + Parser 2")


if __name__ == "__main__":
    main()