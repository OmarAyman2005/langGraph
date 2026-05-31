import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from repair.global_repair_loop import run_interactive_repair_loop


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def print_json(title: str, data: Any) -> None:
    print(title)
    print(pretty_json(data))


def read_multiline_input() -> str:
    print("Manual Test: Global User-Guided Repair Loop")
    print("Pipeline: Full pipeline with retry from Normalizer after failure")
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


def print_available_attempt_outputs(attempt_result: Dict[str, Any]) -> None:
    """
    Prints all available intermediate outputs for one repair-loop attempt.

    Since failed attempts may stop early, each section is printed only if it
    exists in the attempt result.
    """

    print("\nPipeline Success:")
    print(attempt_result.get("pipeline_success"))

    print("\nPipeline Status:")
    print(attempt_result.get("pipeline_status"))

    print("\nError Component:")
    print(attempt_result.get("error_component"))

    print("\nError Message:")
    print(attempt_result.get("error_message"))

    # ==================================================
    # Normalizer
    # ==================================================
    if "normalizer_result" in attempt_result:
        print_json("\nNormalizer Result:", attempt_result["normalizer_result"])

    if "normalized_input" in attempt_result:
        print("\nNormalized Input:")
        print(attempt_result["normalized_input"])

    # ==================================================
    # Parser 1
    # ==================================================
    if "parser_1_result" in attempt_result:
        print_json("\nParser 1 Result:", attempt_result["parser_1_result"])

    if "parsed_problem" in attempt_result:
        print_json("\nParsed Problem:", attempt_result["parsed_problem"])

    # ==================================================
    # LLM Response Generator
    # ==================================================
    if "llm_generation_result" in attempt_result:
        print_json("\nLLM Generation Result:", attempt_result["llm_generation_result"])

    if "raw_llm_output" in attempt_result:
        print("\nRaw LLM Output:")
        print(attempt_result["raw_llm_output"])

    # ==================================================
    # Parser 2
    # ==================================================
    if "parser_2_result" in attempt_result:
        print_json("\nParser 2 Result:", attempt_result["parser_2_result"])

    if "parsed_trace" in attempt_result:
        print_json("\nParsed Trace:", attempt_result["parsed_trace"])

    # ==================================================
    # Translator
    # ==================================================
    if "translation_result" in attempt_result:
        print_json("\nTranslation Result:", attempt_result["translation_result"])

    if "symbolic_problem" in attempt_result:
        print_json("\nSymbolic Problem:", attempt_result["symbolic_problem"])

    if "symbolic_trace" in attempt_result:
        print_json("\nSymbolic Trace:", attempt_result["symbolic_trace"])

    # ==================================================
    # Verifier
    # ==================================================
    if "verification_result" in attempt_result:
        print_json("\nVerification Result:", attempt_result["verification_result"])

    # ==================================================
    # Final Result
    # ==================================================
    if "final_result" in attempt_result:
        print_json("\nFinal Result:", attempt_result["final_result"])


def print_final_summary(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 100)
    print("FINAL REPAIR LOOP RESULT")
    print("=" * 100)

    print("Repair Loop Success:")
    print(result["repair_loop_success"])

    print("\nRepair Loop Status:")
    print(result["repair_loop_status"])

    print("\nAttempts Used:")
    print(result["attempts_used"])

    print("\nFinal Error:")
    print(result["final_error"])

    final_pipeline_result = result.get("final_pipeline_result")

    if final_pipeline_result:
        print("\nFinal Pipeline Status:")
        print(final_pipeline_result.get("pipeline_status"))

        if final_pipeline_result.get("pipeline_success"):
            print("\nFinal Normalized Input:")
            print(final_pipeline_result.get("normalized_input"))

            print("\nFinal Verification Result:")
            print(pretty_json(final_pipeline_result.get("verification_result")))


def print_attempts_summary(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 100)
    print("FULL ATTEMPTS DETAILS")
    print("=" * 100)

    for attempt in result["attempts"]:
        attempt_result = attempt["result"]

        print("\n" + "=" * 100)
        print(f"ATTEMPT {attempt['attempt_number']} — FULL DETAILS")
        print("=" * 100)

        print("\nRaw Input:")
        print(attempt["raw_input"])

        print_available_attempt_outputs(attempt_result)


def main() -> None:
    initial_raw_input = read_multiline_input()

    result = run_interactive_repair_loop(
        initial_raw_input=initial_raw_input,
        max_repair_attempts=3,
    )

    print_final_summary(result)
    print_attempts_summary(result)


if __name__ == "__main__":
    main()