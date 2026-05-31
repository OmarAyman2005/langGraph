import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from repair.global_repair_loop import run_pipeline_with_repair_inputs


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


TEST_CASES = [
    {
        "name": "repair missing question",
        "inputs": [
            "Ahmed studies. Sara sleeps.",
            "Ahmed studies. Sara sleeps. Does Ahmed study?",
        ],
        "expected_success": True,
        "expected_attempts_used": 2,
    },
    {
        "name": "repair empty input",
        "inputs": [
            "",
            "Ahmed studies. Does Ahmed study?",
        ],
        "expected_success": True,
        "expected_attempts_used": 2,
    },
    {
        "name": "repair unsupported premise",
        "inputs": [
            "All cats are animals. Ahmed studies. Does Ahmed study?",
            "Ahmed studies. Does Ahmed study?",
        ],
        "expected_success": True,
        "expected_attempts_used": 2,
    },
    {
        "name": "repair unsupported question",
        "inputs": [
            "Ahmed studies. What does Ahmed do?",
            "Ahmed studies. Does Ahmed study?",
        ],
        "expected_success": True,
        "expected_attempts_used": 2,
    },
    {
        "name": "success without repair",
        "inputs": [
            "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        ],
        "expected_success": True,
        "expected_attempts_used": 1,
    },
    {
        "name": "fails after max repair attempts",
        "inputs": [
            "",
            "",
            "",
            "",
        ],
        "expected_success": False,
        "expected_attempts_used": 4,
    },
]


def main() -> None:
    passed = 0
    total = len(TEST_CASES)

    print("=" * 100)
    print("Automated Test: Global User-Guided Repair Loop")
    print("Pipeline: Full pipeline with retry from Normalizer after failure")
    print("=" * 100)

    for index, case in enumerate(TEST_CASES, start=1):
        print("=" * 100)
        print(f"TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        result = run_pipeline_with_repair_inputs(
            raw_inputs=case["inputs"],
            max_repair_attempts=3,
        )

        print("Repair Loop Result:")
        print(pretty_json(
            {
                "repair_loop_success": result["repair_loop_success"],
                "repair_loop_status": result["repair_loop_status"],
                "attempts_used": result["attempts_used"],
                "final_error": result["final_error"],
            }
        ))

        for attempt in result["attempts"]:
            attempt_result = attempt["result"]
            print("\nAttempt:", attempt["attempt_number"])
            print("Raw Input:")
            print(attempt["raw_input"])
            print("Pipeline Success:", attempt_result["pipeline_success"])
            print("Error Component:", attempt_result.get("error_component"))
            print("Error Message:", attempt_result.get("error_message"))

        success_ok = result["repair_loop_success"] == case["expected_success"]
        attempts_ok = result["attempts_used"] == case["expected_attempts_used"]

        if success_ok and attempts_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected success:", case["expected_success"])
            print("Actual success:", result["repair_loop_success"])
            print("Expected attempts:", case["expected_attempts_used"])
            print("Actual attempts:", result["attempts_used"])

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {passed}/{total}")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()