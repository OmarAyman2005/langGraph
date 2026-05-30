import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.normalized_prompt_parser import parse_normalized_prompt


def read_multiline_input() -> str:
    print("Manual Test: Parser 1 — Normalized Prompt Parser")
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


def main() -> None:
    normalized_input = read_multiline_input()

    print("\n" + "=" * 100)
    print("NORMALIZED INPUT:")
    print(normalized_input)

    print("\n" + "-" * 100)
    print("PARSER 1 — NORMALIZED PROMPT PARSER")

    result = parse_normalized_prompt(normalized_input)

    if result["prompt_parse_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(result.get("prompt_parse_error"))

        print("\nFull Parser Result:")
        pprint(result)

        print("\nFinal Result: FAILED at Parser 1")
        return

    print("Status: PASSED")

    parsed_problem = result["problem"]

    print("\nParsed Problem Object:")
    pprint(parsed_problem)

    print("\nPremises:")
    for premise_id, premise in parsed_problem["premises"].items():
        print(f"{premise_id}: {premise}")

    print("\nQuestion:")
    print(parsed_problem["question"])

    print("\nFinal Result: PASSED Parser 1")


if __name__ == "__main__":
    main()