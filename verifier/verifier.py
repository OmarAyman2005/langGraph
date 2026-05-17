from typing import Dict, Any


def apply_modus_ponens(a: str, b: str):
    candidates = [(a, b), (b, a)]

    for first, second in candidates:
        if "->" in first:
            left, right = [x.strip() for x in first.split("->", 1)]
            if second.strip() == left:
                return right

    return None


def verify_symbolic_trace(
    symbolic_problem: Dict[str, Any], symbolic_trace: Dict[str, Any]
) -> Dict[str, Any]:
    if not symbolic_problem:
        return {
            "verification_success": False,
            "verification_error": "Missing symbolic problem.",
            "verification_result": None,
        }

    if not symbolic_trace:
        return {
            "verification_success": False,
            "verification_error": "Missing symbolic trace.",
            "verification_result": None,
        }

    premises = symbolic_problem.get("premises", {})
    target = symbolic_problem.get("target")
    answer = symbolic_trace.get("answer")
    steps = symbolic_trace.get("steps", [])
    special_case = symbolic_trace.get("special_case")

    available = dict(premises)
    step_results = []
    derived_facts = set()

    # Special case handling
    if special_case == "Target Not Found in Premises":
        target_found_directly = target in premises.values()

        final_answer_check = (
            "consistent"
            if (answer == "not_entailed" and not target_found_directly)
            else "inconsistent"
        )

        return {
            "verification_success": True,
            "verification_error": None,
            "verification_result": {
                "validity": (
                    "valid" if final_answer_check == "consistent" else "invalid"
                ),
                "step_results": [],
                "final_answer_check": final_answer_check,
            },
        }

    for step in steps:
        sid = step["id"]
        supports = step["supports"]
        rule = step["rule"]
        derived = step["derived"]

        missing_supports = [s for s in supports if s not in available]
        if missing_supports:
            step_results.append(
                {
                    "id": sid,
                    "valid": False,
                    "error": f"missing_supports: {missing_supports}",
                    "derived": derived,
                }
            )
            continue

        support_values = [available[s] for s in supports]

        if rule == "Modus Ponens":
            if len(support_values) != 2:
                step_results.append(
                    {
                        "id": sid,
                        "valid": False,
                        "error": "Modus Ponens requires exactly 2 supports.",
                        "derived": derived,
                    }
                )
                continue

            expected = apply_modus_ponens(support_values[0], support_values[1])

            if expected != derived:
                step_results.append(
                    {
                        "id": sid,
                        "valid": False,
                        "error": f"expected '{expected}' but got '{derived}'",
                        "derived": derived,
                    }
                )
                continue

        else:
            step_results.append(
                {
                    "id": sid,
                    "valid": False,
                    "error": f"Unsupported rule in verifier v1: {rule}",
                    "derived": derived,
                }
            )
            continue

        # Valid step
        available[sid] = derived
        derived_facts.add(derived)

        step_results.append(
            {
                "id": sid,
                "valid": True,
                "error": None,
                "derived": derived,
            }
        )

    all_steps_valid = all(step["valid"] for step in step_results)

    if answer == "entailed":
        final_answer_check = "consistent" if target in derived_facts else "inconsistent"
    elif answer == "not_entailed":
        final_answer_check = (
            "consistent" if target not in derived_facts else "inconsistent"
        )
    else:
        final_answer_check = "inconsistent"

    overall_validity = (
        "valid"
        if (all_steps_valid and final_answer_check == "consistent")
        else "invalid"
    )

    return {
        "verification_success": True,
        "verification_error": None,
        "verification_result": {
            "validity": overall_validity,
            "step_results": step_results,
            "final_answer_check": final_answer_check,
        },
    }
