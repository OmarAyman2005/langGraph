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
from normalizer.sentence_pattern_matcher import match_sentence_patterns
from normalizer.question_pattern_matcher import validate_question_pattern
from normalizer.subject_propagator import propagate_subjects


TEST_CASES = [
    {
        "name": "empty input fails at N1",
        "input": "",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "non-English input fails at N1",
        "input": "Ahmed studies 😊. Does Ahmed pass?",
        "expected_stage": "N1",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊",
    },
    {
        "name": "no question mark fails at N2",
        "input": "Ahmed studies. Sara sleeps.",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "two yes-no questions fail at N2",
        "input": "Ahmed studies. Does Ahmed pass? Is Sara happy?",
        "expected_stage": "N2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
        "name": "question only fails at N3",
        "input": "Does Ahmed pass?",
        "expected_stage": "N3",
        "expected_success": False,
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "unsupported premise fails at N4",
        "input": "All cats are animals. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N4",
        "expected_success": False,
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },
    {
        "name": "unsupported question target fails at N5",
        "input": "Ahmed studies. Is Ahmed taller than Sara?",
        "expected_stage": "N5",
        "expected_success": False,
        "expected_error_contains": "Question target does not map into a supported atomic proposition",
    },

    # ==================================================
    # VALID N6 — no propagation needed
    # ==================================================
    {
        "name": "facts unchanged",
        "input": "Ahmed studies. Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies.",
            "sara sleeps.",
        ],
    },
    {
        "name": "explicit conditional unchanged",
        "input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "explicit conjunction unchanged",
        "input": "Ahmed studies and Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and sara sleeps.",
        ],
    },
    {
        "name": "explicit disjunction unchanged",
        "input": "Ahmed studies or Sara sleeps. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies or sara sleeps.",
        ],
    },

    # ==================================================
    # VALID N6 — premise propagation only
    # ==================================================
    {
        "name": "conditional he propagation",
        "input": "If Ahmed studies, then he passes. Ahmed studies. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "if ahmed studies, then ahmed passes.",
            "ahmed studies.",
        ],
    },
    {
        "name": "conditional she propagation",
        "input": "If Sara trains, then she wins. Sara trains. Does Sara win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does sara win?",
        "expected_premises": [
            "if sara trains, then sara wins.",
            "sara trains.",
        ],
    },
    {
        "name": "conditional it propagation with determiner subject",
        "input": "If the sensor is active, then it rings. The sensor is active. Does the sensor ring?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does the sensor ring?",
        "expected_premises": [
            "if the sensor is active, then the sensor rings.",
            "the sensor is active.",
        ],
    },
    {
        "name": "conditional they propagation",
        "input": "If the guards arrive, then they wait. The guards arrive. Do the guards wait?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "do the guards wait?",
        "expected_premises": [
            "if the guards arrive, then the guards wait.",
            "the guards arrive.",
        ],
    },
    {
        "name": "conjunction he propagation",
        "input": "Ahmed studies and he passes. Does Ahmed pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed pass?",
        "expected_premises": [
            "ahmed studies and ahmed passes.",
        ],
    },
    {
        "name": "conjunction it propagation",
        "input": "The sensor is active and it rings. Does the sensor ring?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does the sensor ring?",
        "expected_premises": [
            "the sensor is active and the sensor rings.",
        ],
    },
    {
        "name": "disjunction she propagation",
        "input": "Sara studies or she sleeps. Does Sara sleep?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does sara sleep?",
        "expected_premises": [
            "sara studies or sara sleeps.",
        ],
    },
    {
        "name": "disjunction it propagation",
        "input": "The door opens or it closes. Does the door close?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does the door close?",
        "expected_premises": [
            "the door opens or the door closes.",
        ],
    },

    # ==================================================
    # VALID N6 — premise + question propagation
    # ==================================================
    {
        "name": "conditional and question he propagation",
        "input": "If Ahmed plays, then he wins. He plays. Does he win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed win?",
        "expected_premises": [
            "if ahmed plays, then ahmed wins.",
            "ahmed plays.",
        ],
    },
    {
        "name": "conjunction and question she propagation",
        "input": "Sara studies and she passes. Does she pass?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does sara pass?",
        "expected_premises": [
            "sara studies and sara passes.",
        ],
    },
    {
        "name": "determiner subject and question it propagation",
        "input": "The sensor is active and it rings. Does it ring?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does the sensor ring?",
        "expected_premises": [
            "the sensor is active and the sensor rings.",
        ],
    },

    # ==================================================
    # N6 AMBIGUITY CASES
    # ==================================================
    {
        "name": "ambiguous conjunction source rejected",
        "input": "Ahmed helps Sara and she studies. Does Sara study?",
        "expected_stage": "N6",
        "expected_success": False,
        "expected_error_contains": "Ambiguous subject propagation detected",
        "expected_failed_premises": ["ahmed helps sara and she studies."],
    },
    {
        "name": "ambiguous conditional source rejected",
        "input": "If Ahmed meets Sara, then she smiles. Does Sara smile?",
        "expected_stage": "N6",
        "expected_success": False,
        "expected_error_contains": "Ambiguous subject propagation detected",
        "expected_failed_premises": ["if ahmed meets sara, then she smiles."],
    },
    {
        "name": "ambiguous determiner source rejected",
        "input": "If the sensor triggers the alarm, then it rings. Does the sensor ring?",
        "expected_stage": "N6",
        "expected_success": False,
        "expected_error_contains": "Ambiguous subject propagation detected",
        "expected_failed_premises": ["if the sensor triggers the alarm, then it rings."],
    },
    {
        "name": "question pronoun resolved from single fact subject",
        "input": "Ahmed plays. Does he win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "does ahmed win?",
        "expected_premises": [
            "ahmed plays.",
        ],
    },
    {
        "name": "question pronoun with multiple propagated sources rejected",
        "input": "Ahmed studies and he passes. Sara trains and she wins. Does he pass?",
        "expected_stage": "N6",
        "expected_success": False,
        "expected_error_contains": "Ambiguous subject propagation detected",
    },
    {
        "name": "same-sentence missing subject with modal in disjunction",
        "input": "Hany will travel or will stay home. Will Hany travel?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "will hany travel?",
        "expected_premises": [
            "hany will travel or hany will stay home.",
        ],
    },
    {
        "name": "same-sentence missing subject with repeated verb in disjunction",
        "input": "Ahmed plays football or plays tennis. Is Ahmed good?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "is ahmed good?",
        "expected_premises": [
            "ahmed plays football or ahmed plays tennis.",
        ],
    },
    {
        "name": "cross-sentence premise and question pronoun propagation",
        "input": "Ahmed plays football. He eats pizza. Will he win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "will ahmed win?",
        "expected_premises": [
            "ahmed plays football.",
            "ahmed eats pizza.",
        ],
    },
    {
        "name": "question pronoun resolved from single concrete subject",
        "input": "Ahmed plays football. Is he good?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "is ahmed good?",
        "expected_premises": [
            "ahmed plays football.",
        ],
    },
    {
        "name": "pronoun-only premises and question stay unchanged",
        "input": "He played. He won. Did he win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "did he win?",
        "expected_premises": [
            "he played.",
            "he won.",
        ],
    },
    {
        "name": "different pronoun subjects stay unchanged",
        "input": "He plays piano. She smiles. Will they win?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "will they win?",
        "expected_premises": [
            "he plays piano.",
            "she smiles.",
        ],
    },
    {
        "name": "global concrete subject resolves pronoun conditional and question",
        "input": "Mariam practices daily. If she practices daily then she improves. Will she improve?",
        "expected_stage": "N6",
        "expected_success": True,
        "expected_question": "will mariam improve?",
        "expected_premises": [
            "mariam practices daily.",
            "if mariam practices daily, then mariam improves.",
        ],
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return expected.lower() in actual.lower()


def print_test_header(index: int, total: int, name: str, raw_input: str) -> None:
    print("=" * 80)
    print(f"TEST {index}/{total} — {name}")
    print("-" * 80)
    print("Input:")
    print(raw_input)


def print_expected(case: dict) -> None:
    print("\nExpected:")
    if case["expected_success"]:
        print("SUCCESS at N6")
        print(f"Question: {case.get('expected_question')}")
        print("Subject-Propagated Premises:")
        for premise in case.get("expected_premises", []):
            print(f"- {premise}")
    else:
        print(f"FAIL at {case['expected_stage']}")
        print(f"Error contains: {case.get('expected_error_contains')}")
        if case.get("expected_failed_premises"):
            print("Expected Failed Premises:")
            for premise in case["expected_failed_premises"]:
                print(f"- {premise}")


def print_actual_success(question: str, premises: list[str], normalized_input: str) -> None:
    print("\nActual:")
    print("SUCCESS at N6")
    print(f"Question: {question}")
    print("Subject-Propagated Premises:")
    for premise in premises:
        print(f"- {premise}")
    print("Normalized Input:")
    print(normalized_input)


def print_actual_failure(stage: str, error: str | None, failed_premises: list[str] | None = None) -> None:
    print("\nActual:")
    print(f"FAIL at {stage}")
    print(f"Error: {error}")
    if failed_premises:
        print("Failed Premises:")
        for premise in failed_premises:
            print(f"- {premise}")


def run_tests() -> None:
    passed = 0
    total = len(TEST_CASES)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"], case["input"])
        print_expected(case)

        n1_result = unify_case(case["input"])

        if n1_result["success"] is False:
            actual_stage = "N1"
            actual_error = n1_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N1"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 raw result: {n1_result}")
            continue

        n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])

        if n2_result["success"] is False:
            actual_stage = "N2"
            actual_error = n2_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N2"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
            continue

        n3_result = segment_and_validate_premises(
            n2_result["candidate_premise_text"]
        )

        if n3_result["success"] is False:
            actual_stage = "N3"
            actual_error = n3_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N3"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
            continue

        n4_result = match_sentence_patterns(n3_result["premises"])

        if n4_result["success"] is False:
            actual_stage = "N4"
            actual_error = n4_result.get("error")
            print_actual_failure(
                actual_stage,
                actual_error,
                n4_result.get("failed_premises", []),
            )

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N4"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
            continue

        n5_result = validate_question_pattern(n2_result["question"])

        if n5_result["success"] is False:
            actual_stage = "N5"
            actual_error = n5_result.get("error")
            print_actual_failure(actual_stage, actual_error)

            if (
                case["expected_success"] is False
                and case["expected_stage"] == "N5"
                and contains(actual_error, case.get("expected_error_contains"))
            ):
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
            continue

        n6_result = propagate_subjects(
            premises=n4_result["pattern_matched_premises"],
            question=n2_result["question"],
        )

        if n6_result["success"] is False:
            actual_stage = "N6"
            actual_error = n6_result.get("error")
            failed_premises = n6_result.get("failed_premises", [])
            print_actual_failure(actual_stage, actual_error, failed_premises)

            success_ok = case["expected_success"] is False
            stage_ok = case["expected_stage"] == "N6"
            error_ok = contains(actual_error, case.get("expected_error_contains"))

            expected_failed = case.get("expected_failed_premises")
            failed_ok = True
            if expected_failed is not None:
                failed_ok = failed_premises == expected_failed

            if success_ok and stage_ok and error_ok and failed_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nDebug:")
                print(f"N1 output: {n1_result.get('case_unified_input')}")
                print(f"N2 raw result: {n2_result}")
                print(f"N3 raw result: {n3_result}")
                print(f"N4 raw result: {n4_result}")
                print(f"N5 raw result: {n5_result}")
                print(f"N6 raw result: {n6_result}")
            continue

        actual_question = n6_result["subject_propagated_question"]
        actual_premises = n6_result["subject_propagated_premises"]

        actual_normalized_input = build_normalized_prompt(
            premises=actual_premises,
            question=actual_question,
        )

        print_actual_success(
            actual_question,
            actual_premises,
            actual_normalized_input,
        )

        success_ok = case["expected_success"] is True
        question_ok = actual_question == case.get("expected_question")
        premises_ok = actual_premises == case.get("expected_premises")

        if success_ok and question_ok and premises_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("\nDebug:")
            print(f"N1 output: {n1_result.get('case_unified_input')}")
            print(f"N2 raw result: {n2_result}")
            print(f"N3 raw result: {n3_result}")
            print(f"N4 raw result: {n4_result}")
            print(f"N5 raw result: {n5_result}")
            print(f"N6 raw result: {n6_result}")
            print(f"Built normalized input: {actual_normalized_input}")

    print("=" * 80)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()