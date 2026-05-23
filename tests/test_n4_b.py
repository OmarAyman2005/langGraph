import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.sentence_pattern_matcher import match_sentence_patterns


def read_premises():
    print("Manual Test: Normalizer N4 Only")
    print("Paste one premise per line.")
    print("When finished, type END on a new line.")
    print("=" * 100)

    premises = []

    while True:
        line = input()
        if line.strip() == "END":
            break

        if line.strip():
            premises.append(line.strip())

    return premises


def main():
    premises = read_premises()

    print("\n" + "=" * 100)
    print("INPUT PREMISES:")
    for i, premise in enumerate(premises, start=1):
        print(f"{i}. {premise}")

    print("\n" + "-" * 100)
    print("N4: SENTENCE PATTERN MATCH")
    n4 = match_sentence_patterns(premises)
    print(n4)

    if not n4["success"]:
        print("\nFINAL RESULT: FAILED at N4")

        print("ERRORS:")
        for error in n4["errors"]:
            print(f"- {error}")

        failed_premises = n4.get("failed_premises", [])

        if failed_premises:
            print("\nFAILED PREMISE(S):")
            for premise in failed_premises:
                print(f"- {premise}")

        return

    print("\nPATTERN-MATCHED PREMISES:")
    for i, premise in enumerate(n4["pattern_matched_premises"], start=1):
        print(f"{i}. {premise}")

    print("\nFINAL RESULT: PASSED N4")


if __name__ == "__main__":
    main()