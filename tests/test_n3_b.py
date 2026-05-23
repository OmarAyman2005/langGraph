import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import (
    segment_and_validate_premises,
    build_normalized_prompt,
)


def read_multiline_input() -> str:
    print("Manual Test: Normalizer N1 + N2 + N3")
    print("N1: Character Adjuster / Case Unifier")
    print("N2: Question Detector")
    print("N3: Premises Separator")
    print("Paste one raw input.")
    print("When finished, type END on a new line.")
    print("=" * 80)

    lines = []

    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def main() -> None:
    raw_input = read_multiline_input()

    print("\n" + "=" * 80)
    print("RAW INPUT:")
    print(raw_input)

    # -------------------------------
    # N1
    # -------------------------------
    print("\n" + "-" * 80)
    print("N1 — CHARACTER ADJUSTER")

    n1_result = unify_case(raw_input)

    if n1_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n1_result.get("errors", []):
            print(f"- {error}")

        print("\nFinal Result: FAILED at N1")
        return

    print("Status: PASSED")
    print("Case-Unified Input:")
    print(n1_result["case_unified_input"])

    # -------------------------------
    # N2
    # -------------------------------
    print("\n" + "-" * 80)
    print("N2 — QUESTION DETECTOR")

    n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

    if n2_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n2_result.get("errors", []):
            print(f"- {error}")

        print("\nFinal Result: FAILED at N2")
        return

    print("Status: PASSED")
    print("Extracted Question:")
    print(n2_result["question"])

    print("\nCandidate Premise Text:")
    print(n2_result["candidate_premise_text"])

    # -------------------------------
    # N3
    # -------------------------------
    print("\n" + "-" * 80)
    print("N3 — PREMISES SEPARATOR")

    n3_result = segment_and_validate_premises(
        n2_result["candidate_premise_text"]
    )

    if n3_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n3_result.get("errors", []):
            print(f"- {error}")

        print("\nFinal Result: FAILED at N3")
        return

    print("Status: PASSED")

    print("Separated Premises:")
    for i, premise in enumerate(n3_result["premises"], start=1):
        print(f"{i}. {premise}")

    normalized_input = build_normalized_prompt(
        premises=n3_result["premises"],
        question=n2_result["question"],
    )

    print("\nNormalized Input:")
    print(normalized_input)

    print("\nFinal Result: PASSED N1 + N2 + N3")


if __name__ == "__main__":
    main()