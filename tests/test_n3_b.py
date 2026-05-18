import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import segment_and_validate_premises


def read_multiline_input():
    print("Manual Test: Normalizer N1 + N2 + N3")
    print("N1: Case Unification")
    print("N2: Question Detection")
    print("N3: Premise Separation")
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


def main():
    raw_input = read_multiline_input()

    print("\n" + "=" * 100)
    print("RAW INPUT:")
    print(raw_input)

    print("\n" + "-" * 100)
    print("N1: CASE UNIFICATION")
    n1 = unify_case(raw_input)
    print(n1)

    if not n1["success"]:
        print("\nFINAL RESULT: FAILED at N1")
        print(n1["error"])
        return

    print("\nCASE-UNIFIED INPUT:")
    print(n1["case_unified_input"])

    print("\n" + "-" * 100)
    print("N2: QUESTION DETECTION")
    n2 = detect_single_yes_no_question(n1["case_unified_input"])
    print(n2)

    if not n2["success"]:
        print("\nFINAL RESULT: FAILED at N2")
        print("ERRORS:")
        for error in n2["errors"]:
            print(f"- {error}")
        return

    print("\nEXTRACTED QUESTION:")
    print(n2["question"])

    print("\nCANDIDATE PREMISE TEXT:")
    print(n2["candidate_premise_text"])

    print("\n" + "-" * 100)
    print("N3: PREMISE SEPARATION")
    n3 = segment_and_validate_premises(n2["candidate_premise_text"])
    print(n3)

    if not n3["success"]:
        print("\nFINAL RESULT: FAILED at N3")
        print("ERRORS:")
        for error in n3["errors"]:
            print(f"- {error}")
        return

    print("\nSEPARATED PREMISES:")
    for i, premise in enumerate(n3["premises"], start=1):
        print(f"{i}. {premise}")

    print("\nFINAL RESULT: PASSED N1 + N2 + N3")


if __name__ == "__main__":
    main()