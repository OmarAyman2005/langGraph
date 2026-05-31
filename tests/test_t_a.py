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
from tests.test_utils import pretty_json

CUMULATIVE_TEST_CASES = [
    {
        "name": "empty normalized prompt fails at parser 1",
        "normalized_input": "",
        "expected_success": False,
        "expected_stage": "parser_1",
        "expected_error_contains": "Empty normalized prompt",
    },
    {
        "name": "missing question section fails at parser 1",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies."
        ),
        "expected_success": False,
        "expected_stage": "parser_1",
        "expected_error_contains": "Missing Question section",
    },
    {
        "name": "modus ponens entailed",
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
        "name": "multi-step chain",
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
        "name": "conjunction elimination",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies and sara sleeps.\n"
            "\n"
            "Question:\n"
            "does sara sleep?"
        ),
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism",
        "normalized_input": (
            "Premises:\n"
            "1. ahmed studies or sara sleeps.\n"
            "2. not sara sleeps.\n"
            "\n"
            "Question:\n"
            "does ahmed study?"
        ),
        "expected_success": True,
    },
    {
        "name": "target not found special case",
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
        "name": "direct fact case may be logically invalid later but should translate",
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


DIRECT_TRANSLATOR_TEST_CASES = [
    # ==================================================
    # VALID TRANSLATION CASES
    # ==================================================
    {
        "name": "translate modus ponens problem and trace",
        "parsed_problem": {
            "premises": {
                "P1": "if ahmed studies, then ahmed passes.",
                "P2": "ahmed studies.",
            },
            "question": "does ahmed pass?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "ahmed passes.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "AhmedPasses",
        },
        "expected_symbolic_trace": {
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
    },
    {
        "name": "translate modus tollens-style negated target",
        "parsed_problem": {
            "premises": {
                "P1": "if ahmed studies, then ahmed passes.",
                "P2": "not ahmed passes.",
            },
            "question": "does ahmed not study?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "not ahmed studies.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Tollens",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "~AhmedPasses",
            },
            "target": "~AhmedStudies",
        },
        "expected_symbolic_trace": {
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
    },
    {
        "name": "translate chain with article removal in symbols",
        "parsed_problem": {
            "premises": {
                "P1": "if it rains, then the ground is wet.",
                "P2": "if the ground is wet, then the match is cancelled.",
                "P3": "it rains.",
            },
            "question": "is the match cancelled?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "the ground is wet.",
                    "supports": ["P1", "P3"],
                    "rule": "Modus Ponens",
                },
                {
                    "id": "S2",
                    "statement": "the match is cancelled.",
                    "supports": ["S1", "P2"],
                    "rule": "Modus Ponens",
                },
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
                "P2": "GroundIsWet -> MatchIsCancelled",
                "P3": "ItRains",
            },
            "target": "MatchIsCancelled",
        },
        "expected_symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "GroundIsWet",
                    "supports": ["P1", "P3"],
                    "rule": "Modus Ponens",
                },
                {
                    "id": "S2",
                    "derived": "MatchIsCancelled",
                    "supports": ["S1", "P2"],
                    "rule": "Modus Ponens",
                },
            ],
            "special_case": None,
        },
    },
    {
        "name": "translate conjunction and disjunction premises",
        "parsed_problem": {
            "premises": {
                "P1": "ahmed studies and sara sleeps.",
                "P2": "omar plays or nada wins.",
            },
            "question": "does sara sleep?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "sara sleeps.",
                    "supports": ["P1"],
                    "rule": "Conjunction Elimination",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies & SaraSleeps",
                "P2": "OmarPlays | NadaWins",
            },
            "target": "SaraSleeps",
        },
        "expected_symbolic_trace": {
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
    },
    {
        "name": "translate target not found special case",
        "parsed_problem": {
            "premises": {
                "P1": "if it rains, then the ground is wet.",
                "P2": "it rains.",
            },
            "question": "is the sky blue?",
        },
        "parsed_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
                "P2": "ItRains",
            },
            "target": "SkyIsBlue",
        },
        "expected_symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
    },
    {
        "name": "translate not entailed because opposite is derivable",
        "parsed_problem": {
            "premises": {
                "P1": "if ahmed studies, then ahmed passes.",
                "P2": "ahmed studies.",
            },
            "question": "does ahmed not pass?",
        },
        "parsed_trace": {
            "answer": "not_entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "ahmed passes.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies -> AhmedPasses",
                "P2": "AhmedStudies",
            },
            "target": "~AhmedPasses",
        },
        "expected_symbolic_trace": {
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
    },

    # ==================================================
    # INVALID TRANSLATION CASES
    # ==================================================
    {
        "name": "missing parsed problem",
        "parsed_problem": None,
        "parsed_trace": {
            "answer": "entailed",
            "steps": [],
            "special_case": None,
        },
        "expected_success": False,
        "expected_error_contains": "Missing parsed problem",
    },
    {
        "name": "missing parsed trace",
        "parsed_problem": {
            "premises": {
                "P1": "ahmed studies.",
            },
            "question": "does ahmed study?",
        },
        "parsed_trace": None,
        "expected_success": False,
        "expected_error_contains": "Missing parsed trace",
    },
    {
        "name": "unsupported premise pattern",
        "parsed_problem": {
            "premises": {
                "P1": "all cats are animals.",
            },
            "question": "does ahmed study?",
        },
        "parsed_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_success": False,
        "expected_error_contains": "Unsupported sentence pattern in premise P1",
    },
    {
        "name": "unsupported question pattern",
        "parsed_problem": {
            "premises": {
                "P1": "ahmed studies.",
            },
            "question": "what does ahmed do?",
        },
        "parsed_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_success": False,
        "expected_error_contains": "Unsupported question pattern",
    },
    {
        "name": "unsupported step statement",
        "parsed_problem": {
            "premises": {
                "P1": "if tom is hungry, then tom eats.",
            },
            "question": "does tom eat?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "tom probably eats.",
                    "supports": ["P1"],
                    "rule": "Modus Ponens",
                }
            ],
            "special_case": None,
        },
        "expected_success": False,
        "expected_error_contains": "Unsupported sentence pattern in step S1",
    },
    {
        "name": "translate no derivation found special case",
        "parsed_problem": {
            "premises": {
                "P1": "if it rains, then the ground is wet.",
            },
            "question": "is the ground wet?",
        },
        "parsed_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "No Derivation Found",
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "ItRains -> GroundIsWet",
            },
            "target": "GroundIsWet",
        },
        "expected_symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "No Derivation Found",
        },
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
    print("CUMULATIVE TESTS: Parser 1 + LLM Response Generator + Parser 2 + Translator")
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
                print(parser_1_result)

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

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "parser_2"
            error_ok = contains(
                parser_2_result.get("response_parse_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(parser_2_result)

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

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "translator"
            error_ok = contains(
                translation_result.get("translation_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(translation_result)

            continue

        print("\nTRANSLATOR: PASSED")
        print("Symbolic Problem:")
        print(pretty_json(translation_result["symbolic_problem"]))
        print("Symbolic Trace:")
        print(pretty_json(translation_result["symbolic_trace"]))
        print("Proposition Map:")
        print(pretty_json(translation_result["proposition_map"]))

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but cumulative pipeline passed.")

    return passed, total


def run_direct_translation_tests() -> tuple[int, int]:
    print("=" * 100)
    print("DIRECT TESTS: Translator Only")
    print("=" * 100)

    passed = 0
    total = len(DIRECT_TRANSLATOR_TEST_CASES)

    for index, case in enumerate(DIRECT_TRANSLATOR_TEST_CASES, start=1):
        print("=" * 100)
        print(f"DIRECT TEST {index}/{total}: {case['name']}")
        print("-" * 100)

        print("PARSED PROBLEM:")
        print(pretty_json(case["parsed_problem"]))

        print("\nPARSED TRACE:")
        print(pretty_json(case["parsed_trace"]))

        result = translate_problem_and_trace(
            parsed_problem=case["parsed_problem"],
            parsed_trace=case["parsed_trace"],
        )

        if result["translation_success"] is False:
            print("\nTRANSLATOR: FAILED")
            print(result.get("translation_error"))

            success_ok = case["expected_success"] is False
            error_ok = contains(
                result.get("translation_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print(result)

            continue

        print("\nTRANSLATOR: PASSED")
        print("Symbolic Problem:")
        print(pretty_json(result["symbolic_problem"]))
        print("Symbolic Trace:")
        print(pretty_json(result["symbolic_trace"]))
        print("Proposition Map:")
        print(pretty_json(result["proposition_map"]))

        success_ok = case["expected_success"] is True
        problem_ok = result["symbolic_problem"] == case.get("expected_symbolic_problem")
        trace_ok = result["symbolic_trace"] == case.get("expected_symbolic_trace")

        if success_ok and problem_ok and trace_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected symbolic problem:")
            print(pretty_json(case.get("expected_symbolic_problem")))
            print("Actual symbolic problem:")
            print(result["symbolic_problem"])

            print("\nExpected symbolic trace:")
            print(pretty_json(case.get("expected_symbolic_trace")))
            print("Actual symbolic trace:")
            print(result["symbolic_trace"])

    return passed, total


def main() -> None:
    cumulative_passed, cumulative_total = run_cumulative_tests()
    direct_passed, direct_total = run_direct_translation_tests()

    total_passed = cumulative_passed + direct_passed
    total = cumulative_total + direct_total

    print("=" * 100)
    print(f"FINAL SUMMARY: PASSED {total_passed}/{total}")
    print(f"- Cumulative: {cumulative_passed}/{cumulative_total}")
    print(f"- Direct Translator: {direct_passed}/{direct_total}")

    if total_passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()