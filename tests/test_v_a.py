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
from verifier.verifier import verify_symbolic_trace


def pretty_json(data) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


CUMULATIVE_TEST_CASES = [
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
    # VALID RAW INPUTS — FULL PIPELINE THROUGH VERIFIER
    # ==================================================
    {
        "name": "modus ponens full pipeline",
        "raw_input": "If Ahmed studies, then Ahmed passes. Ahmed studies. Does Ahmed pass?",
        "expected_success": True,
    },
    {
        "name": "conjunction elimination full pipeline",
        "raw_input": "Ahmed studies and Sara sleeps. Does Ahmed study?",
        "expected_success": True,
    },
    {
        "name": "disjunctive syllogism full pipeline",
        "raw_input": "Ahmed studies or Sara sleeps. Ahmed does not study. Does Sara sleep?",
        "expected_success": True,
    },
    {
        "name": "target not found full pipeline",
        "raw_input": "If it rains, then the ground is wet. It rains. Is the sky blue?",
        "expected_success": True,
    },
    {
        "name": "direct fact full pipeline may have invalid explanation",
        "raw_input": "The door is open. Is the door open?",
        "expected_success": True,
    },
    {
        "name": "synonym unification before verifier",
        "raw_input": "Ahmed starts. Sara begins. Does Sara begin?",
        "expected_success": True,
    },
    {
        "name": "antonym unification before verifier",
        "raw_input": "The door is open. Is the door closed?",
        "expected_success": True,
    },
    {
        "name": "synonym then antonym unification before verifier",
        "raw_input": "The door is open. The window is shut. Is the window closed?",
        "expected_success": True,
    },
    {
        "name": "verb antonym unification before verifier",
        "raw_input": "Ahmed passes. Sara fails. Does Sara fail?",
        "expected_success": True,
    },
]

CLOSURE_LIMIT_CYCLE_PREMISES = {
    f"P{i + 1}": f"A{i} -> A{(i + 1) % 18}"
    for i in range(18)
}

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
    # NEW NORMALIZER-COMPATIBLE VERIFIER CASES
    # ==================================================
    {
        "name": "valid normalized antonym output as direct premise",
        "symbolic_problem": {
            "premises": {
                "P1": "DoorIsOpen",
                "P2": "~WindowIsOpen",
            },
            "target": "~WindowIsOpen",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "~WindowIsOpen",
                    "supports": ["P2"],
                    "rule": "Conjunction Elimination",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
        "expected_final_answer_check": "consistent",
    },
    {
        "name": "valid verb antonym target already in premises",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedPasses",
                "P2": "~SaraPasses",
            },
            "target": "~SaraPasses",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "~SaraPasses",
                    "supports": ["P1", "P2"],
                    "rule": "Disjunctive Syllogism",
                }
            ],
            "special_case": None,
        },
        "expected_verification_success": True,
        "expected_validity": "invalid",
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
    {
        "name": "system failure direct contradictory premises",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies",
                "P2": "~AhmedStudies",
            },
            "target": "SaraSleeps",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_verification_success": False,
        "expected_error_contains": "Contradictory premises detected",
    },
    {
        "name": "system failure contradiction inside conjunction premise",
        "symbolic_problem": {
            "premises": {
                "P1": "AhmedStudies & ~AhmedStudies",
            },
            "target": "SaraSleeps",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "Target Not Found in Premises",
        },
        "expected_verification_success": False,
        "expected_error_contains": "Contradictory premises detected",
    },
    {
        "name": "cycle-safe no derivation found without starting fact",
        "symbolic_problem": {
            "premises": {
                "P1": "A -> B",
                "P2": "B -> A",
            },
            "target": "A",
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
        "name": "cycle-safe derivation with starting fact",
        "symbolic_problem": {
            "premises": {
                "P1": "A -> B",
                "P2": "B -> A",
                "P3": "A",
            },
            "target": "B",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "B",
                    "supports": ["P1", "P3"],
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
        "name": "self-loop implication does not prove atom",
        "symbolic_problem": {
            "premises": {
                "P1": "A -> A",
            },
            "target": "A",
        },
        "symbolic_trace": {
            "answer": "entailed",
            "steps": [
                {
                    "id": "S1",
                    "derived": "A",
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
        "name": "self-loop no derivation found is valid",
        "symbolic_problem": {
            "premises": {
                "P1": "A -> A",
            },
            "target": "A",
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
        "name": "system failure closure safety limit exceeded",
        "symbolic_problem": {
            "premises": CLOSURE_LIMIT_CYCLE_PREMISES,
            "target": "A0",
        },
        "symbolic_trace": {
            "answer": "not_entailed",
            "steps": [],
            "special_case": "No Derivation Found",
        },
        "expected_verification_success": False,
        "expected_error_contains": "Closure safety limit exceeded",
    },
]


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
    print("CUMULATIVE TESTS: Full Normalizer + Parser 1 + LLM Response Generator + Parser 2 + Translator + Verifier")
    print(
        "Pipeline: Raw Input → N1 → N2 → N3 → N4 → N5 → N6 → N7 → N8 "
        "→ Parser 1 → LLM Response → Parser 2 → Translator → Verifier"
    )
    print("=" * 100)

    passed = 0
    total = len(CUMULATIVE_TEST_CASES)

    for index, case in enumerate(CUMULATIVE_TEST_CASES, start=1):
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

        # ==================================================
        # Verifier
        # ==================================================
        verification_result = verify_symbolic_trace(
            symbolic_problem=translation_result["symbolic_problem"],
            symbolic_trace=translation_result["symbolic_trace"],
        )

        if verification_result["verification_success"] is False:
            print("\nVERIFIER SYSTEM FAILURE:")
            print(verification_result["verification_error"])

            success_ok = case["expected_success"] is False
            stage_ok = case.get("expected_stage") == "verifier"
            error_ok = contains(
                verification_result.get("verification_error"),
                case.get("expected_error_contains"),
            )

            if success_ok and stage_ok and error_ok:
                print("\nResult: PASS")
                passed += 1
            else:
                print("\nResult: FAIL")
                print("\nFull Verification Result:")
                print(pretty_json(verification_result))

            continue

        print("\nVERIFIER: COMPLETED")
        print("\nVerification Result:")
        print(pretty_json(verification_result["verification_result"]))

        if case["expected_success"] is True:
            print("\nResult: PASS")
            passed += 1
        else:
            print("\nResult: FAIL")
            print("Expected failure but full pipeline through Verifier passed.")

    return passed, total


def run_direct_verifier_tests() -> tuple[int, int]:
    print("=" * 100)
    print("DIRECT TESTS: Verifier Only")
    print("=" * 100)

    passed = 0
    total = len(DIRECT_VERIFIER_TEST_CASES)

    for index, case in enumerate(DIRECT_VERIFIER_TEST_CASES, start=1):
        print_test_header(index, total, case["name"])

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