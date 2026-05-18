import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case


def main():
    print("Manual Test: Normalizer Component N1 — Case Unification")
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

    result = unify_case(raw_input)

    print("\nCASE UNIFICATION RESULT:")
    print(result)

    if result["success"] is False:
        print("\nFINAL RESULT: FAILED at N1")
        print(result["error"])
        return

    print("\nCASE-UNIFIED INPUT:")
    print(result["case_unified_input"])

    print("\nFINAL RESULT: PASSED N1")


if __name__ == "__main__":
    main()
