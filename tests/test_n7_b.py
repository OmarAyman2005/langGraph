import sys
from pathlib import Path
from pprint import pprint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question
from normalizer.premise_segmenter import (
    segment_and_validate_premises,
    build_normalized_prompt,
)
from normalizer.sentence_pattern_matcher import match_sentence_patterns
from normalizer.question_pattern_matcher import validate_question_pattern
from normalizer.subject_propagator import propagate_subjects
from normalizer.synonym_words_unifier import unify_synonym_words


def read_multiline_input() -> str:
    print("Manual Test: Normalizer N1 + N2 + N3 + N4 + N5 + N6 + N7")
    print("N1: Character Adjuster / Case Unifier")
    print("N2: Question Detector")
    print("N3: Premises Separator")
    print("N4: Sentence Pattern Matcher")
    print("N5: Question Pattern Matcher")
    print("N6: Subject Propagation")
    print("N7: Synonym Words Unifier")
    print("Design: N7 uses NLTK WordNet only, no local lists, no LLM calls.")
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

    # -------------------------------
    # N4
    # -------------------------------
    print("\n" + "-" * 80)
    print("N4 — SENTENCE PATTERN MATCHER")

    n4_result = match_sentence_patterns(n3_result["premises"])

    if n4_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n4_result.get("errors", []):
            print(f"- {error}")

        failed_premises = n4_result.get("failed_premises", [])
        if failed_premises:
            print("\nFailed Premise(s):")
            for premise in failed_premises:
                print(f"- {premise}")

        print("\nFinal Result: FAILED at N4")
        return

    print("Status: PASSED")
    print("Pattern-Matched Premises:")
    for i, premise in enumerate(n4_result["pattern_matched_premises"], start=1):
        print(f"{i}. {premise}")

    # -------------------------------
    # N5
    # -------------------------------
    print("\n" + "-" * 80)
    print("N5 — QUESTION PATTERN MATCHER")

    n5_result = validate_question_pattern(n2_result["question"])

    if n5_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n5_result.get("errors", []):
            print(f"- {error}")

        print("\nFinal Result: FAILED at N5")
        return

    print("Status: PASSED")
    print("Original Question:")
    print(n2_result["question"])

    print("\nTarget Candidate(s) Before Subject Propagation:")
    for i, target in enumerate(n5_result["target_candidates"], start=1):
        print(f"{i}. {target}")

    print("\nPrimary Target Before Subject Propagation:")
    print(n5_result["primary_target"])

    # -------------------------------
    # N6
    # -------------------------------
    print("\n" + "-" * 80)
    print("N6 — SUBJECT PROPAGATION")

    n6_result = propagate_subjects(
        premises=n4_result["pattern_matched_premises"],
        question=n2_result["question"],
    )

    if n6_result["success"] is False:
        print("Status: FAILED")
        print("Errors:")
        for error in n6_result.get("errors", []):
            print(f"- {error}")

        failed_premises = n6_result.get("failed_premises", [])
        if failed_premises:
            print("\nFailed Premise(s):")
            for premise in failed_premises:
                print(f"- {premise}")

        print("\nFinal Result: FAILED at N6")
        return

    print("Status: PASSED")

    print("Subject-Propagated Premises:")
    for i, premise in enumerate(n6_result["subject_propagated_premises"], start=1):
        print(f"{i}. {premise}")

    print("\nSubject-Propagated Question:")
    print(n6_result["subject_propagated_question"])

    propagated_subjects = n6_result.get("propagated_subjects", [])
    if propagated_subjects:
        print("\nPropagated Subject(s):")
        for subject in propagated_subjects:
            print(f"- {subject}")
    else:
        print("\nPropagated Subject(s):")
        print("- None")

    n6_normalized_input = build_normalized_prompt(
        premises=n6_result["subject_propagated_premises"],
        question=n6_result["subject_propagated_question"],
    )

    print("\nNormalized Prompt After N6:")
    print(n6_normalized_input)

    # -------------------------------
    # N7
    # -------------------------------
    print("\n" + "-" * 80)
    print("N7 — SYNONYM WORDS UNIFIER")

    n7_result = unify_synonym_words(n6_normalized_input)

    if n7_result["success"] is False:
        print("Status: FAILED")
        print("Error:")
        print(n7_result.get("error"))

        print("\nFull N7 Result:")
        pprint(n7_result)

        print("\nFinal Result: FAILED at N7")
        return

    print("Status: PASSED")

    print("\nSynonym Change(s):")
    changes = n7_result.get("changes", [])

    if changes:
        pprint(changes)
    else:
        print("- None")

    print("\nNormalized Prompt So Far After N7:")
    print(n7_result["text"])

    print("\nFinal Result: PASSED N1 + N2 + N3 + N4 + N5 + N6 + N7")


if __name__ == "__main__":
    main()