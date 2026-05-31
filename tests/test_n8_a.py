import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.semantic_lexicon import wordnet_is_available
from normalizer.antonym_words_unifier import unify_antonym_words


TEST_CASES = [
    {
        "name": "open closed question",
        "input": (
            "Premises:\n"
            "1. the door is open.\n"
            "\n"
            "Question:\n"
            "is the door closed?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. the door is open.\n"
            "\n"
            "Question:\n"
            "is the door not open?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "open closed premise",
        "input": (
            "Premises:\n"
            "1. the door is open.\n"
            "2. the window is closed.\n"
            "\n"
            "Question:\n"
            "is the door open?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. the door is open.\n"
            "2. not the window is open.\n"
            "\n"
            "Question:\n"
            "is the door open?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "good bad question",
        "input": (
            "Premises:\n"
            "1. ahmed is good.\n"
            "\n"
            "Question:\n"
            "is sara bad?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. ahmed is good.\n"
            "\n"
            "Question:\n"
            "is sara not good?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "good bad premise",
        "input": (
            "Premises:\n"
            "1. ahmed is good.\n"
            "2. sara is bad.\n"
            "\n"
            "Question:\n"
            "is ahmed good?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. ahmed is good.\n"
            "2. not sara is good.\n"
            "\n"
            "Question:\n"
            "is ahmed good?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "pass fail question",
        "input": (
            "Premises:\n"
            "1. ahmed passes.\n"
            "\n"
            "Question:\n"
            "does sara fail?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. ahmed passes.\n"
            "\n"
            "Question:\n"
            "does sara not pass?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "pass fail premise",
        "input": (
            "Premises:\n"
            "1. ahmed passes.\n"
            "2. sara fails.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. ahmed passes.\n"
            "2. not sara passes.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "no antonym no change",
        "input": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_text": (
            "Premises:\n"
            "1. ahmed studies.\n"
            "2. sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_changes_count_at_least": 0,
    },
]


def run_tests() -> None:
    if not wordnet_is_available():
        print("NLTK WordNet is not available.")
        print("Run:")
        print("python -c \"import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')\"")
        raise SystemExit(1)

    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: N8 — Antonym Words Unifier")
    print("Design: NLTK WordNet only, no local lists, no LLM calls.")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print("=" * 100)
        print(f"TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        print("INPUT:")
        print(case["input"])

        result = unify_antonym_words(case["input"])

        print("\nRESULT:")
        pprint(result)

        success_ok = result["success"] is True
        text_ok = result.get("text") == case["expected_text"]
        changes_ok = len(result.get("changes", [])) >= case["expected_changes_count_at_least"]

        if success_ok and text_ok and changes_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected text:")
            print(case["expected_text"])
            print("Actual text:")
            print(result.get("text"))
            print("Expected minimum changes:")
            print(case["expected_changes_count_at_least"])
            print("Actual changes:")
            print(len(result.get("changes", [])))

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()