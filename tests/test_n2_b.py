import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question


def main():
    print("Manual Test: Normalizer N1 + N2")
    print("N1: Case Unification")
    print("N2: Question Detection")
    print("Paste one raw input.")
    print("When finished, type END on a new line.")
    print("=" * 100)

    lines = []

    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    raw_input = "\n".join(lines)

    print("\n" + "=" * 100)
    print("RAW INPUT:")
    print(raw_input)

    print("\n" + "-" * 100)
    print("N1: CASE UNIFICATION")

    n1_result = unify_case(raw_input)
    print(n1_result)

    if n1_result["success"] is False:
        print("\nFINAL RESULT: FAILED at N1")
        print("ERRORS:")
        for error in n1_result.get("errors", []):
            print(f"- {error}")
        return

    print("\nCASE-UNIFIED INPUT:")
    print(n1_result["case_unified_input"])

    print("\n" + "-" * 100)
    print("N2: QUESTION DETECTION")

    n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])
    print(n2_result)

    if n2_result["success"] is False:
        print("\nFINAL RESULT: FAILED at N2")
        print("ERRORS:")
        for error in n2_result.get("errors", []):
            print(f"- {error}")
        return

    print("\nEXTRACTED QUESTION:")
    print(n2_result["question"])

    print("\nCANDIDATE PREMISE TEXT:")
    print(n2_result["candidate_premise_text"])

    print("\nFINAL RESULT: PASSED N1 + N2")


if __name__ == "__main__":
    main()
