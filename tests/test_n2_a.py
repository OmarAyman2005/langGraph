import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.case_unifier import unify_case
from normalizer.question_detector import detect_single_yes_no_question

TEST_CASES = [
    # --------------------------------------------------
    # N1 FAILURE CASES
    # --------------------------------------------------
    {
        "name": "empty input fails at n1",
        "input": "",
        "expected_stage": "n1",
        "expected_success": False,
        "expected_error_contains": "Empty input",
    },
    {
        "name": "non-english input fails at n1",
        "input": "Ahmed studies 😊. Does Ahmed pass?",
        "expected_stage": "n1",
        "expected_success": False,
        "expected_error_contains": "Non-English character(s) found: 😊",
    },
    {
        "name": "unsupported character fails at n1",
        "input": "Ahmed studies @ school. Does Ahmed pass?",
        "expected_stage": "n1",
        "expected_success": False,
        "expected_error_contains": "Unsupported character(s) found: @",
    },
    # --------------------------------------------------
    # VALID N2 CASES
    # --------------------------------------------------
    {
        "name": "valid does-question with question mark",
        "input": "Ahmed studies. Does Ahmed pass?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "does ahmed pass",
        "expected_candidate_contains": "ahmed studies",
    },
    {
        "name": "valid does-question without question mark",
        "input": "Ahmed studies. Does Ahmed pass",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "does ahmed pass",
        "expected_candidate_contains": "ahmed studies",
    },
    {
        "name": "valid is-question",
        "input": "The ground is wet. Is the ground wet?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "is the ground wet",
        "expected_candidate_contains": "the ground is wet",
    },
    {
        "name": "valid will-question",
        "input": "Ahmed studies. Will Ahmed pass?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "will ahmed pass",
        "expected_candidate_contains": "ahmed studies",
    },
    {
        "name": "valid can-question",
        "input": "The machine is ready. Can the machine start?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "can the machine start",
        "expected_candidate_contains": "the machine is ready",
    },
    {
        "name": "valid has-question",
        "input": "Ahmed trains. Has Ahmed won?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "has ahmed won",
        "expected_candidate_contains": "ahmed trains",
    },
    # --------------------------------------------------
    # VALID INLINE PUNCTUATION-FREE CASES
    # --------------------------------------------------
    {
        "name": "inline final is-question without punctuation",
        "input": "Ahmed Played Menna Cried if Ahmed Won Talaat Wins is Talaat winning",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "is talaat winning",
        "expected_candidate_contains": "ahmed played menna cried if ahmed won talaat wins",
    },
    {
        "name": "inline final does-question without punctuation",
        "input": "Ahmed studies Sara sleeps does Ahmed pass",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "does ahmed pass",
        "expected_candidate_contains": "ahmed studies sara sleeps",
    },
    {
        "name": "inline final will-question without punctuation",
        "input": "Ahmed studies Sara sleeps will Ahmed pass",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "will ahmed pass",
        "expected_candidate_contains": "ahmed studies sara sleeps",
    },
    # --------------------------------------------------
    # N2 FAILURE: NO YES/NO QUESTION
    # --------------------------------------------------
    {
        "name": "no yes-no question declarative only",
        "input": "Ahmed studies. Sara sleeps.",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "declarative be verb should not become question",
        "input": "Ahmed is tired. Sara sleeps.",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "declarative be verb without punctuation should not become question",
        "input": "Ahmed is tired Sara sleeps",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "malformed auxiliary-led sequence is not question",
        "input": "Ahmed studies is tired sara sleeps",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected",
    },
    # --------------------------------------------------
    # N2 FAILURE: MORE THAN ONE YES/NO QUESTION
    # --------------------------------------------------
    {
        "name": "two explicit yes-no questions",
        "input": "Ahmed studies. Does Ahmed pass? Is Ahmed happy?",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
        "name": "two line-separated yes-no questions without question marks",
        "input": "Ahmed studies.\nDoes Ahmed pass\nIs Ahmed happy",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
        "name": "two inline yes-no questions without punctuation",
        "input": "Ahmed studies does Ahmed pass is Sara happy",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    # --------------------------------------------------
    # N2 FAILURE: WH / NON YES-NO QUESTION
    # --------------------------------------------------
    {
        "name": "wh question only",
        "input": "Ahmed studies. What does Ahmed do?",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "No yes/no question detected\nNon yes/no question detected",
    },
    {
        "name": "wh question plus yes-no question",
        "input": "Ahmed studies. What does Ahmed do? Does Ahmed pass?",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    {
        "name": "inline wh question plus yes-no question",
        "input": "Ahmed studies what does Ahmed do does Ahmed pass",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "Non yes/no question detected",
    },
    # --------------------------------------------------
    # QUESTION ONLY SHOULD PASS N2
    # N3 will later fail because there are no candidate premises.
    # --------------------------------------------------
    {
        "name": "question only passes n2 with empty candidate premises",
        "input": "Does Ahmed pass?",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "does ahmed pass",
        "expected_candidate_contains": "",
    },
    {
        "name": "line-separated middle yes-no question",
        "input": """
Ahmed is Amazing
Did he eat pizza
Sara is Crazy
""",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "did he eat pizza",
        "expected_candidate_contains": "ahmed is amazing",
    },
    {
        "name": "single-stream middle yes-no question",
        "input": "Ahmed is Amazing Did he eat pizza Sara is Crazy",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "did he eat pizza",
        "expected_candidate_contains": "ahmed is amazing",
    },
    {
        "name": "middle is-question followed by extra premise text",
        "input": "Ahmed sleeps is Ahmed great I am ultimate",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "is ahmed great",
        "expected_candidate_contains": "ahmed sleeps",
    },
    {
        "name": "middle will-question followed by extra premise text",
        "input": "Sara waits will Ahmed travel the machine stops",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "will ahmed travel",
        "expected_candidate_contains": "sara waits",
    },
    {
        "name": "middle can-question followed by extra premise text",
        "input": "The alarm rings can the guard wake up the door opens",
        "expected_stage": "n2",
        "expected_success": True,
        "expected_question_contains": "can the guard wake up",
        "expected_candidate_contains": "the alarm rings",
    },
    {
        "name": "two middle is-questions with extra premise text",
        "input": "am I ok He is Perfect is it Good She is Good",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
        "name": "middle am-question plus will-question",
        "input": "he is Good Am i Good Will He DO",
        "expected_stage": "n2",
        "expected_success": False,
        "expected_error_contains": "More than one yes/no question detected",
    },
    {
    "name": "incomplete is-question should not be detected",
    "input": "is Ahmed Sara is Great",
    "expected_stage": "n2",
    "expected_success": False,
    "expected_error_contains": "No yes/no question detected",
    },
    {
    "name": "two declarative be sentences should not become questions",
    "input": "Sara is Amzing Ahmed is Great",
    "expected_stage": "n2",
    "expected_success": False,
    "expected_error_contains": "No yes/no question detected",
    },
]


def assert_contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def run_tests():
    passed = 0

    for case in TEST_CASES:
        print("=" * 100)
        print(f"TEST: {case['name']}")
        print("RAW INPUT:")
        print(case["input"])

        print("\n" + "-" * 100)
        print("N1: CASE UNIFICATION")

        n1_result = unify_case(case["input"])
        print(n1_result)

        if n1_result["success"] is False:
            if case["expected_stage"] != "n1":
                print("\nFAIL: failed at N1 but expected to reach N2")
                continue

            if not assert_contains(
                n1_result.get("error"), case.get("expected_error_contains")
            ):
                print("\nFAIL: N1 error mismatch")
                print(f"Expected: {case.get('expected_error_contains')}")
                print(f"Actual:   {n1_result.get('error')}")
                continue

            print("\nPASS")
            passed += 1
            continue

        print("\n" + "-" * 100)
        print("N2: QUESTION DETECTION")

        n2_result = detect_single_yes_no_question(n1_result["case_unified_input"])
        print(n2_result)

        if case["expected_stage"] == "n1":
            print("\nFAIL: expected failure at N1, but reached N2")
            continue

        actual_success = n2_result["success"]
        expected_success = case["expected_success"]

        if actual_success != expected_success:
            print("\nFAIL: N2 wrong success value")
            print(f"Expected success={expected_success}, got success={actual_success}")
            continue

        if expected_success is False:
            if not assert_contains(
                n2_result.get("error"), case.get("expected_error_contains")
            ):
                print("\nFAIL: N2 error mismatch")
                print(f"Expected: {case.get('expected_error_contains')}")
                print(f"Actual:   {n2_result.get('error')}")
                continue

            print("\nPASS")
            passed += 1
            continue

        if not assert_contains(
            n2_result.get("question"), case.get("expected_question_contains")
        ):
            print("\nFAIL: question mismatch")
            print(
                f"Expected question to contain: {case.get('expected_question_contains')}"
            )
            print(f"Actual question: {n2_result.get('question')}")
            continue

        expected_candidate = case.get("expected_candidate_contains")
        actual_candidate = n2_result.get("candidate_premise_text")

        if expected_candidate != "":
            if not assert_contains(actual_candidate, expected_candidate):
                print("\nFAIL: candidate premise text mismatch")
                print(f"Expected candidate to contain: {expected_candidate}")
                print(f"Actual candidate: {actual_candidate}")
                continue
        else:
            if actual_candidate != "":
                print("\nFAIL: expected empty candidate premise text")
                print(f"Actual candidate: {actual_candidate}")
                continue

        print("\nPASS")
        passed += 1

    print("=" * 100)
    print(f"PASSED {passed}/{len(TEST_CASES)}")


if __name__ == "__main__":
    run_tests()
