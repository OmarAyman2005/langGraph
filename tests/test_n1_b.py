import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case


def read_multiline_input() -> str:
    print("Manual Test: Normalizer Component N1 — Character Adjuster / Case Unifier")
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


def main() -> None:
    raw_input = read_multiline_input()

    print("\n" + "=" * 100)
    print("RAW INPUT:")
    print(raw_input)

    print("\n" + "-" * 100)
    print("N1: CHARACTER ADJUSTER / CASE UNIFIER")

    result = unify_case(raw_input)
    print(result)

    if result["success"] is False:
        print("\nFINAL RESULT: FAILED at N1")
        print("ERRORS:")
        for error in result.get("errors", []):
            print(f"- {error}")

        debug = result.get("debug", {})
        non_english = debug.get("non_english_characters", [])
        unsupported = debug.get("unsupported_characters", [])

        if non_english:
            print("\nNON-ENGLISH CHARACTER(S):")
            for ch in non_english:
                print(f"- {repr(ch)}")

        if unsupported:
            print("\nUNSUPPORTED CHARACTER(S):")
            for ch in unsupported:
                print(f"- {repr(ch)}")

        return

    print("\nCASE-UNIFIED INPUT:")
    print(result["case_unified_input"])

    print("\nDEBUG:")
    print(result.get("debug", {}))

    print("\nFINAL RESULT: PASSED N1")


if __name__ == "__main__":
    main()