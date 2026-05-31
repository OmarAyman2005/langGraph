import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.semantic_lexicon import wordnet_is_available
from normalizer.synonym_words_unifier import unify_synonym_words


TEST_CASES = [
    {
        "name": "begin replaced with earlier start",
        "input": "ahmed starts. sara begins.",
        "expected_success": True,
        "expected_text": "ahmed starts. sara starts.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "start replaced with earlier begin with inflection",
        "input": "ahmed begins. sara starts.",
        "expected_success": True,
        "expected_text": "ahmed begins. sara begins.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "big and large adjective synonym",
        "input": "the box is big. the bag is large.",
        "expected_success": True,
        "expected_text": "the box is big. the bag is big.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "large and big adjective synonym reverse order",
        "input": "the box is large. the bag is big.",
        "expected_success": True,
        "expected_text": "the box is large. the bag is large.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "correct and right synonym",
        "input": "the answer is correct. the solution is right.",
        "expected_success": True,
        "expected_text": "the answer is correct. the solution is correct.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "closed and shut synonym",
        "input": "the door is closed. the window is shut.",
        "expected_success": True,
        "expected_text": "the door is closed. the window is closed.",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "question base verb adapts earlier starts to start",
        "input": "ahmed starts. does sara begin?",
        "expected_success": True,
        "expected_text": "ahmed starts. does sara start?",
        "expected_changes_count_at_least": 1,
    },
    {
        "name": "no synonym no change",
        "input": "ahmed studies. sara sleeps.",
        "expected_success": True,
        "expected_text": "ahmed studies. sara sleeps.",
        "expected_changes_count_at_least": 0,
    },
    {
        "name": "same word repeated no change",
        "input": "ahmed studies. sara studies.",
        "expected_success": True,
        "expected_text": "ahmed studies. sara studies.",
        "expected_changes_count_at_least": 0,
    },
    {
        "name": "function words ignored",
        "input": "the light is on. ahmed is on the team.",
        "expected_success": True,
        "expected_text": "the light is on. ahmed is on the team.",
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
    print("Automated Test: N7 — Synonym Words Unifier")
    print("Design: NLTK WordNet only, no local lists, no LLM calls.")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print("=" * 100)
        print(f"TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        print("INPUT:")
        print(case["input"])

        result = unify_synonym_words(case["input"])

        print("\nRESULT:")
        pprint(result)

        success_ok = result["success"] is case["expected_success"]
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