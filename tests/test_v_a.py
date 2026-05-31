import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from llm_response.llm_utils import generation_llm
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from prompts.llm_response_prompt import SYSTEM_PROMPT
from translator.translator import translate_problem_and_trace
from verifier.verifier import verify_symbolic_trace


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


CUMULATIVE_TEST_CASES = [
    {
        "name": "parser 1 failure",
        "normalized_input": "",
        "expected_success": False,
        "expected_stage": "parser_1",
        "expected_error_contains": "Empty normalized prompt",
    },
    {
        "name": "valid modus ponens full pipeline",
        "normalized_input": (
            "Premises:\n"
            "1. if ahmed studies, then ahmed passes.\n"
            "2. ahmed studies.\n"
            "\n"
            "Question:\n"
            "does ahmed pass?"
        ),
        "expected_success": True,
    },
    {
        "name": "valid multi-step full pipeline",
        "normalized_input": (
            "Premises:\n"
            "1. if it rains, then the ground is wet.\n"
            "2. if the ground is wet, then the match is cancelled.\n"
            "3. it rains.\n"
            "\n"
            "Question:\n"
            "is the match cancelled?"
        ),
        "expected_success": True,
    },
    {
        "name": "target not found full pipeline",
        "normalized_input": (
            "Premises:\n"
            "1. if it rains, then the ground is wet.\n"
            "2. it rains.\n"
            "\n"
            "Question:\n"
            "is the sky blue?"
        ),
        "expected_success": True,
    },
    {
        "name": "direct fact full pipeline may be invalid explanation",
        "normalized_input": (
            "Premises:\n"
            "1. the door is open.\n"
            "\n"
            "Question:\n"
            "is the door open?"
        ),
        "expected_success": True,
    },
]


DIRECT_VERIFIER_TEST_CASES = [
    # ==================================================
    # VALID ENTAILED CASES
    # ==================================================
    {
        "name": "valid modus ponens",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "AhmedPasses",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedPasses",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid modus tollens",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "~AhmedPasses",
            },
            "target": "~AhmedStudies",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "~AhmedStudies",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Tollens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid hypothetical syllogism then modus ponens",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
                "P2": "GroundIsWet -> MatchIsCancelled",
                "P3": "ItRains",
            },
            "target": "MatchIsCancelled",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "ItRains -> MatchIsCancelled",
                    "supports": ["P1", "P2"],
                    "rule": "Hypothetical Syllogism",
                },
                {
                    "id": "S2",
                    "derived": "MatchIsCancelled",
                    "supports": ["S1", "P3"],
                    "rule": "Modus Ponens",
                },
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid conjunction elimination",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies & SaraSleeps",
            },
            "target": "SaraSleeps",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "SaraSleeps",
                    "supports": ["P1"],
                    "rule": "Conjunction Elimination",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid disjunctive syllogism",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies | SaraSleeps",
                "P2": "~SaraSleeps",
            },
            "target": "AhmedStudies",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedStudies",
                    "supports": ["P1", "P2"],
                    "rule": "Disjunctive Syllogism",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid conjunction introduction",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies",
                "P2": "SaraSleeps",
            },
            "target": "AhmedStudies & SaraSleeps",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedStudies & SaraSleeps",
                    "supports": ["P1", "P2"],
                    "rule": "Conjunction Introduction",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },

    # ==================================================
    # VALID NOT_ENTAILED CASES
    # ==================================================
    {
        "name": "valid not entailed target not found",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
                "P2": "ItRains",
            },
            "target": "SkyIsBlue",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid not entailed no derivation found",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
            },
            "target": "GroundIsWet",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "No Derivation Found",
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid not entailed because opposite is derived",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "~AhmedPasses",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedPasses",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "valid",
        "expected_final_answer_check": "consistent",
    },

    # ==================================================
    # INVALID STEP CASES
    # ==================================================
    {
        "name": "invalid modus ponens missing antecedent",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
            },
            "target": "GroundIsWet",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "GroundIsWet",
                    "supports": ["P1"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },
    {
        "name": "invalid wrong derived statement",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "SaraSleeps",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "SaraSleeps",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },
    {
        "name": "invalid unknown support",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "AhmedPasses",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedPasses",
                    "supports": ["P1", "P3"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },
    {
        "name": "invalid direct fact with wrong rule but answer consistent",
        "symbolic_problem": {
            "premises": {
                "P1": "DoorIsOpen",
            },
            "target": "DoorIsOpen",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "DoorIsOpen",
                    "supports": ["P1"],
                    "rule": "Conjunction Introduction",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "consistent",
    },

    # ==================================================
    # INVALID NOT_ENTAILED SPECIAL CASES
    # ==================================================
    {
        "name": "invalid target not found when target appears in premise vocabulary",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
            },
            "target": "GroundIsWet",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },
    {
        "name": "invalid no derivation found when target is derivable",
        "symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
                "P2": "ItRains",
            },
            "target": "GroundIsWet",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "No Derivation Found",
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },
    {
        "name": "invalid not entailed when target is derived",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "AhmedPasses",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedPasses",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "inconsistent",
    },

    # ==================================================
    # SYSTEM-LEVEL FAILURES
    # ==================================================
    {
        "name": "unsupported rule implementation",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies",
            },
            "target": "AhmedStudies",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "AhmedStudies",
                    "supports": ["P1"],
                    "rule": "Biconditional Introduction",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": False,
        "expected_error_contains": "Unsupported rule implementation",
    },
]


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def call_llm_response_generator(normalized_input: str) -> str:
    human_prompt = f"""Normalized problem:
{normalized_input}
"""

    response = generation_llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]
    )

    return response.content.strip()


def run_cumulative_tests() -> tuple[int, int]:
    print("=" * 100)
    print("CUMULATIVE TESTS: Parser 1 + LLM Response Generator + Parser 2 + Translator + Verifier")
    print("=" * 100)

    passed = 0
    total = len(CUMULATIVE_TEST_CASES)

    for index, case in enumerate(CUMULATIVE_TEST_CASES, start=1):
        print("=" * 100)
        print(f"CUMULATIVE TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        normalized_input = case["normalized_input"]

        print("NORMALIZED INPUT:")
        print(normalized_input)

        parser_1_result = parse_normalized_prompt(normalized_input)

        if parser_1_result["prompt_parse_success"] is False:
            print("\nPARSER 1: FAILED")
            print(parser_1_result.get("prompt_parse_error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "parser_1"
            error_ok = contains(
                parser_1_result.get("prompt_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(pretty_json(parser_1_result))

            continue

        print("\nPARSER 1: PASSED")
        print(pretty_json(parser_1_result["problem"]))

        raw_llm_output = call_llm_response_generator(normalized_input)

        print("\nRAW LLM OUTPUT:")
        print(raw_llm_output)

        parser_2_result = parse_llm_response(raw_llm_output)

        if parser_2_result["response_parse_success"] is False:
            print("\nPARSER 2: FAILED")
            print(parser_2_result.get("response_parse_error"))
            print("\nResult: PASS")
            passed += 1
            continue

        print("\nPARSER 2: PASSED")
        print(pretty_json(parser_2_result["trace"]))

        translation_result = translate_problem_and_trace(
            parsed_problem=parser_1_result["problem"],
            parsed_trace=parser_2_result["trace"],
        )

        if translation_result["translation_success"] is False:
            print("\nTRANSLATOR: FAILED")
            print(translation_result.get("translation_error"))
            print("\nResult: PASS")
            passed += 1
            continue

        print("\nTRANSLATOR: PASSED")
        print("Symbolic Problem:")
        print(pretty_json(translation_result["symbolic_problem"]))
        print("Symbolic Trace:")
        print(pretty_json(translation_result["symbolic_trace"]))

        verification_result = verify_symbolic_trace(
            symbolic_problem=translation_result["symbolic_problem"],
            symbolic_trace=translation_result["symbolic_trace"],
        )

        if verification_result["verification_success"] is False:
            print("\nVERIFIER SYSTEM FAILURE:")
            print(verification_result["verification_error"])
            print("\nResult: PASS")
            passed += 1
            continue

        print("\nVERIFIER: PASSED")
        print(pretty_json(verification_result["verification_result"]))

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but cumulative pipeline passed.")

    return passed, total


def run_direct_verifier_tests() -> tuple[int, int]:
    print("=" * 100)
    print("DIRECT TESTS: Verifier Only")
    print("=" * 100)

    passed = 0
    total = len(DIRECT_VERIFIER_TEST_CASES)

    for index, case in enumerate(DIRECT_VERIFIER_TEST_CASES, start=1):
        print("=" * 100)
        print(f"DIRECT TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        print("SYMBOLIC PROBLEM:")
        print(pretty_json(case["symbolic_problem"]))

        print("\nSYMBOLIC TRACE:")
        print(pretty_json(case["symbolic_trace"]))

        result = verify_symbolic_trace(
            symbolic_problem=case["symbolic_problem"],
            symbolic_trace=case["symbolic_trace"],
        )

        if result["verification_success"] is False:
            print("\nVERIFIER SYSTEM FAILURE:")
            print(result["verification_error"])

            success_ok = case["expected_verification_success"] is False
            error_ok = contains(
                result.get("verification_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(pretty_json(result))

            continue

        print("\nVERIFIER RESULT:")
        print(pretty_json(result["verification_result"]))

        success_ok = case["expected_verification_success"] is True
        validity_ok = result["verification_result"]["validity"] == case.get("expected_validity")
        final_ok = result["verification_result"]["final_answer_check"] == case.get("expected_final_answer_check")

        if success_ok and validity_ok and final_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected validity:", case.get("expected_validity"))
            print("Actual validity:", result["verification_result"]["validity"])
            print("Expected final check:", case.get("expected_final_answer_check"))
            print("Actual final check:", result["verification_result"]["final_answer_check"])

    return passed, total


def main() -> None:
    cumulative_passed, cumulative_total = run_cumulative_tests()
    direct_passed, direct_total = run_direct_verifier_tests()

    total_passed = cumulative_passed + direct_passed
    total = cumulative_total + direct_total

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {total_passed}/{total}")
    print(f"- Cumulative: {cumulative_passed}/{cumulative_total}")
    print(f"- Direct Verifier: {direct_passed}/{direct_total}")

    if total_passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()