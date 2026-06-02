import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from llm_response.llm_response_generator import generate_raw_llm_response
from translator.translator import translate_problem_and_trace
from verifier.verifier import verify_symbolic_trace


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def read_multiline_input() -> str:
    print("Manual Test: Full Normalizer + Parser 1 + LLM Response Generator + Parser 2 + Translator + Verifier")
    print(
        "Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 "
        "→ Parser 1 → LLM Response → Parser 2 → Translator → Verifier"
    )
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

    print("\nParsed Problem:")
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
        print(pretty_json(parser_2_result))

        print("\nFinal Result: FAILED at Parser 2")
        return

    print("Status: PASSED")

    print("\nParsed Trace:")
    print(pretty_json(parser_2_result["trace"]))

    # ==================================================
    # Translator
    # ==================================================
    print("\n" + "-" * 100)
    print("TRANSLATOR")

    translation_result = translate_problem_and_trace(
        parsed_problem=parser_1_result["problem"],
        parsed_trace=parser_2_result["trace"],
    )

    if translation_result["translation_success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(translation_result.get("translation_error"))

        print("\nFull Translation Result:")
        print(pretty_json(translation_result))

        print("\nFinal Result: FAILED at Translator")
        return

    print("Status: PASSED")

    print("\nSymbolic Problem:")
    print(pretty_json(translation_result["symbolic_problem"]))

    print("\nSymbolic Trace:")
    print(pretty_json(translation_result["symbolic_trace"]))

    print("\nProposition Map:")
    print(pretty_json(translation_result["proposition_map"]))

    # ==================================================
    # Verifier
    # ==================================================
    print("\n" + "-" * 100)
    print("VERIFIER")

    verification_result = verify_symbolic_trace(
        symbolic_problem=translation_result["symbolic_problem"],
        symbolic_trace=translation_result["symbolic_trace"],
    )

    if verification_result["verification_success"] is False:
        print("Status: SYSTEM FAILURE")
        print("Error:")
        print(verification_result.get("verification_error"))

        print("\nFull Verification Result:")
        print(pretty_json(verification_result))

        print("\nFinal Result: FAILED at Verifier System Level")
        return

    print("Status: COMPLETED")

    print("\nVerification Result:")
    print(pretty_json(verification_result["verification_result"]))

    validity = verification_result["verification_result"]["validity"]
    final_answer_check = verification_result["verification_result"]["final_answer_check"]
    not_entailed_reason = verification_result["verification_result"].get("not_entailed_reason", "N/A")

    print("\nFinal Verification Summary:")
    print(f"- Explanation Validity: {validity}")
    print(f"- Final Answer Check: {final_answer_check}")
    print(f"- Not Entailed Reason: {not_entailed_reason}")

    print("\nFinal Result: PASSED Full Pipeline Through Verifier")


if __name__ == "__main__":
    main()