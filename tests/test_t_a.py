import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from normalizer.normalizer import normalize_raw_prompt
from parsers.normalized_prompt_parser import parse_normalized_prompt
from parsers.llm_response_parser import parse_llm_response
from llm_response.llm_response_generator import generate_raw_llm_response
from translator.translator import translate_problem_and_trace


TEST_CASES = [
    # ==================================================
    # INVALID RAW INPUTS — EXPECT NORMALIZER FAILURE
    # ==================================================
    {
        "name": "empty raw input fails at normalizer",
        "raw_input": "",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "Empty input",
    },
    {
        "name": "missing question mark fails at normalizer",
        "raw_input": "Ahmed studies. Sara sleeps.",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No yes/no question detected",
    },
    {
        "name": "question only fails at normalizer",
        "raw_input": "Does Ahmed pass?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "No candidate premises found",
    },
    {
        "name": "unsupported premise fails at normalizer",
        "raw_input": "All cats are animals. Ahmed studies. Does Ahmed study?",
        "expected_success": False,
        "expected_stage": "normalizer",
        "expected_error_contains": "One or more premises do not map into supported sentence patterns",
    },

    # ==================================================
    # VALID RAW INPUTS — FULL PIPELINE THROUGH TRANSLATOR
    # ==================================================
    {
        "name": "modus ponens entailed",
        "raw_input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
    },
    {
        "name": "conjunction elimination",
        "raw_input": "Ahmed studies and Sara sleeps. Does Ahmed study?",
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism",
        "raw_input": "Ahmed studies or Sara sleeps. Ahmed does not study. Does Sara sleep?",
        "expected_success": True,
    },
    {
        "name": "target not found special case",
        "raw_input": "If it rains, then the ground is wet. It rains. Is the sky blue?",
        "expected_success": True,
    },
    {
        "name": "direct fact case may be logically invalid later but should translate",
        "raw_input": "The door is open. Is the door open?",
        "expected_success": True,
    },
    {
        "name": "synonym unification before translator",
        "raw_input": "Ahmed starts. Sara begins. Does Sara begin?",
        "expected_success": True,
    },
    {
        "name": "antonym unification before translator",
        "raw_input": "The door is open. Is the door closed?",
        "expected_success": True,
    },
    {
        "name": "synonym then antonym unification before translator",
        "raw_input": "The door is open. The window is shut. Is the window closed?",
        "expected_success": True,
    },
    {
        "name": "verb antonym unification before translator",
        "raw_input": "Ahmed passes. Sara fails. Does Sara fail?",
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
    # NEW NORMALIZER-COMPATIBLE TRANSLATION CASES
    # ==================================================
    {
        "name": "translate normalized synonym output",
        "parsed_problem": {
            "premises": {
                "P1": "ahmed starts.",
                "P2": "sara starts.",
            },
            "question": "does sara start?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "sara starts.",
                    "supports": ["P1", "P2"],
                    "rule": "Conjunction Introduction",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "AhmedStarts",
                "P2": "SaraStarts",
            },
            "target": "SaraStarts",
        },
        "expected_symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "SaraStarts",
                    "supports": ["P1", "P2"],
                    "rule": "Conjunction Introduction",
                }
            ],
            "special_case": None,
        },
    },
    {
        "name": "translate normalized antonym output",
        "parsed_problem": {
            "premises": {
                "P1": "the door is open.",
            },
            "question": "is the door not open?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "the door is not open.",
                    "supports": ["P1"],
                    "rule": "Modus Tollens",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "DoorIsOpen",
            },
            "target": "~DoorIsOpen",
        },
        "expected_symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "~DoorIsOpen",
                    "supports": ["P1"],
                    "rule": "Modus Tollens",
                }
            ],
            "special_case": None,
        },
    },
    {
        "name": "translate normalized synonym then antonym output",
        "parsed_problem": {
            "premises": {
                "P1": "the door is open.",
                "P2": "not the window is open.",
            },
            "question": "is the window not open?",
        },
        "parsed_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "statement": "the window is not open.",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Tollens",
                }
            ],
            "special_case": None,
        },
        "expected_success": True,
        "expected_symbolic_problem": {
            "premises": {
                "P1": "DoorIsOpen",
                "P2": "~WindowIsOpen",
            },
            "target": "~WindowIsOpen",
        },
        "expected_symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "~WindowIsOpen",
                    "supports": ["P1", "P2"],
                    "rule": "Modus Tollens",
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
]


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def contains(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True

    if actual is None:
        return False

    return expected.lower() in actual.lower()


def call_llm_response_generator(normalized_input: str) -> str:
    return generate_raw_llm_response(normalized_input)


def print_test_header(index: int, total: int, name: str) -> None:
    print("=" * 100)
    print(f"TEST {index}/{total}: {name}")
    print("-" * 100)


def run_cumulative_tests() -> tuple[int, int]:
    print("=" * 100)
    print("CUMULATIVE TESTS: Full Normalizer + Parser 1 + LLM Response Generator + Parser 2 + Translator")
    print(
        "Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 "
        "→ Parser 1 → LLM Response → Parser 2 → Translator"
    )
    print("=" * 100)

    passed = 0
    total = len(TEST_CASES)

    for index, case in enumerate(TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

        raw_input = case["raw_input"]

        print("RAW INPUT:")
        print(raw_input)

        # ==================================================
        # Full Normalizer
        # ==================================================
        normalizer_result = normalize_raw_prompt(raw_input)

        if normalizer_result["success"] is False:
            print("\nNORMALIZER: FAILED")
            print(normalizer_result.get("error"))

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "normalizer"
            error_ok = contains(
                normalizer_result.get("error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nFull Normalizer Result:")
                print(pretty_json(normalizer_result))

            continue

        normalized_input = normalizer_result["normalized_input"]

        print("\nNORMALIZER: PASSED")
        print("\nNORMALIZED INPUT:")
        print(normalized_input)

        # ==================================================
        # Parser 1
        # ==================================================
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
                print("\nFull Parser 1 Result:")
                print(pretty_json(parser_1_result))

            continue

        print("\nPARSER 1: PASSED")
        print("\nParsed Problem:")
        print(pretty_json(parser_1_result["problem"]))

        # ==================================================
        # LLM Response Generator
        # ==================================================
        raw_llm_output = call_llm_response_generator(normalized_input)

        print("\nLLM RESPONSE GENERATOR: GENERATED")
        print("\nRAW LLM OUTPUT:")
        print(raw_llm_output)

        # ==================================================
        # Parser 2
        # ==================================================
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
                print("\nFull Parser 2 Result:")
                print(pretty_json(parser_2_result))

            continue

        print("\nPARSER 2: PASSED")
        print("\nParsed Trace:")
        print(pretty_json(parser_2_result["trace"]))

        # ==================================================
        # Translator
        # ==================================================
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
                print("\nFull Translation Result:")
                print(pretty_json(translation_result))

            continue

        print("\nTRANSLATOR: PASSED")
        print("\nSymbolic Problem:")
        print(pretty_json(translation_result["symbolic_problem"]))

        print("\nSymbolic Trace:")
        print(pretty_json(translation_result["symbolic_trace"]))

        print("\nProposition Map:")
        print(pretty_json(translation_result["proposition_map"]))

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but full pipeline through Translator passed.")

    return passed, total


def run_direct_translation_tests() -> tuple[int, int]:
    print("=" * 100)
    print("DIRECT TESTS: Translator Only")
    print("=" * 100)

    passed = 0
    total = len(DIRECT_TRANSLATOR_TEST_CASES)

    for index, case in enumerate(DIRECT_TRANSLATOR_TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

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
                print("\nFull Translation Result:")
                print(pretty_json(result))

            continue

        print("\nTRANSLATOR: PASSED")
        print("\nSymbolic Problem:")
        print(pretty_json(result["symbolic_problem"]))

        print("\nSymbolic Trace:")
        print(pretty_json(result["symbolic_trace"]))

        print("\nProposition Map:")
        print(pretty_json(result["proposition_map"]))

        success_ok = case["expected_success"] is True
        problem_ok = result["symbolic_problem"] == case.get("expected_symbolic_problem")
        trace_ok = result["symbolic_trace"] == case.get("expected_symbolic_trace")

        if success_ok and problem_ok and trace_ok:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")

            print("\nExpected symbolic problem:")
            print(pretty_json(case.get("expected_symbolic_problem")))

            print("\nActual symbolic problem:")
            print(pretty_json(result["symbolic_problem"]))

            print("\nExpected symbolic trace:")
            print(pretty_json(case.get("expected_symbolic_trace")))

            print("\nActual symbolic trace:")
            print(pretty_json(result["symbolic_trace"]))

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