import re
from typing import Any, Dict, List, Optional, Set, Tuple


SUPPORTED_RULES = {
    "Modus Ponens",
    "Modus Tollens",
    "Hypothetical Syllogism",
    "Disjunctive Syllogism",
    "Conjunction Introduction",
    "Conjunction Elimination",
}

SPECIAL_TARGET_NOT_FOUND = "Target Not Found in Premises"
SPECIAL_NO_DERIVATION_FOUND = "No Derivation Found"

MAX_CLOSURE_ITERATIONS = 20
MAX_CLOSURE_ITEMS = 200


class VerifierError(Exception):
    pass


def make_failure(error: str) -> Dict[str, Any]:
    return {
        "verification_success": False,
        "verification_error": error,
        "verification_result": None,
    }


def make_success(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "verification_success": True,
        "verification_error": None,
        "verification_result": result,
    }


def clean_expr(expr: str) -> str:
    return re.sub(r"\s+", " ", expr.strip())


def is_negation(expr: str) -> bool:
    return clean_expr(expr).startswith("~")


def strip_negation(expr: str) -> str:
    expr = clean_expr(expr)

    if expr.startswith("~"):
        return expr[1:].strip()

    return expr


def opposite_of(expr: str) -> str:
    expr = clean_expr(expr)

    if expr.startswith("~"):
        return expr[1:].strip()

    return f"~{expr}"


def split_binary(expr: str, operator: str) -> Optional[Tuple[str, str]]:
    """
    Splits a symbolic expression by a top-level operator.

    The translator currently produces flat symbolic expressions without nested
    parentheses, so a simple split is enough for this project scope.
    """

    expr = clean_expr(expr)

    if operator not in expr:
        return None

    parts = expr.split(operator)

    if len(parts) != 2:
        return None

    left = clean_expr(parts[0])
    right = clean_expr(parts[1])

    if not left or not right:
        return None

    return left, right


def is_conditional(expr: str) -> bool:
    return split_binary(expr, "->") is not None


def is_conjunction(expr: str) -> bool:
    return split_binary(expr, "&") is not None


def is_disjunction(expr: str) -> bool:
    return split_binary(expr, "|") is not None


def is_literal(expr: str) -> bool:
    """
    A literal is an atomic proposition or its negation.

    Examples:
    - A
    - ~A

    Non-literals:
    - A -> B
    - A & B
    - A | B
    """

    expr = clean_expr(expr)

    if not expr:
        return False

    base = strip_negation(expr)

    return (
        split_binary(base, "->") is None
        and split_binary(base, "&") is None
        and split_binary(base, "|") is None
    )


def find_direct_contradiction(expressions: Set[str]) -> Optional[Tuple[str, str]]:
    """
    Detects direct contradiction among literals.

    Example:
    expressions = {"A", "~A"} => ("A", "~A")

    This intentionally does not treat conditional structures like A -> B as
    contradictory expressions. Only atomic literals are checked.
    """

    cleaned_literals = {
        clean_expr(expr)
        for expr in expressions
        if isinstance(expr, str) and is_literal(expr)
    }

    for expr in cleaned_literals:
        opposite = opposite_of(expr)

        if opposite in cleaned_literals:
            positive = strip_negation(expr)
            negative = f"~{positive}"

            return positive, negative

    return None


def extract_atoms(expr: str) -> Set[str]:
    """
    Extracts atomic propositions from symbolic expressions.

    Examples:
    AhmedStudies -> AhmedPasses      => {AhmedStudies, AhmedPasses}
    ~AhmedPasses                     => {AhmedPasses}
    AhmedStudies & SaraSleeps        => {AhmedStudies, SaraSleeps}
    """

    expr = clean_expr(expr)

    for operator in ["->", "&", "|"]:
        split = split_binary(expr, operator)

        if split is not None:
            left, right = split
            return extract_atoms(left) | extract_atoms(right)

    if expr.startswith("~"):
        return {strip_negation(expr)}

    if not expr:
        return set()

    return {expr}


def premise_vocabulary(symbolic_premises: Dict[str, str]) -> Set[str]:
    vocab = set()

    for expr in symbolic_premises.values():
        vocab |= extract_atoms(expr)

    return vocab


def get_support_expressions(
    supports: List[str],
    available_knowledge: Dict[str, str],
) -> Tuple[Optional[List[str]], Optional[str]]:
    expressions = []

    for support in supports:
        if support not in available_knowledge:
            return None, f"unknown_support: {support}"

        expressions.append(available_knowledge[support])

    return expressions, None


def validate_modus_ponens(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 2:
        return False, "insufficient_supports", None

    for conditional_expr, antecedent_expr in [
        (support_exprs[0], support_exprs[1]),
        (support_exprs[1], support_exprs[0]),
    ]:
        split = split_binary(conditional_expr, "->")

        if split is None:
            continue

        antecedent, consequent = split

        if antecedent_expr == antecedent:
            expected = consequent

            if claimed == expected:
                return True, "", expected

            return False, f"wrong_derived: expected {expected}", expected

    return False, "rule_not_applicable", None


def validate_modus_tollens(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 2:
        return False, "insufficient_supports", None

    for conditional_expr, negated_consequent_expr in [
        (support_exprs[0], support_exprs[1]),
        (support_exprs[1], support_exprs[0]),
    ]:
        split = split_binary(conditional_expr, "->")

        if split is None:
            continue

        antecedent, consequent = split

        if negated_consequent_expr == opposite_of(consequent):
            expected = opposite_of(antecedent)

            if claimed == expected:
                return True, "", expected

            return False, f"wrong_derived: expected {expected}", expected

    return False, "rule_not_applicable", None


def validate_hypothetical_syllogism(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 2:
        return False, "insufficient_supports", None

    first = split_binary(support_exprs[0], "->")
    second = split_binary(support_exprs[1], "->")

    if first is None or second is None:
        return False, "rule_not_applicable", None

    a, b = first
    c, d = second

    possible_expected = []

    if b == c:
        possible_expected.append(f"{a} -> {d}")

    if d == a:
        possible_expected.append(f"{c} -> {b}")

    for expected in possible_expected:
        if claimed == expected:
            return True, "", expected

    if possible_expected:
        return False, f"wrong_derived: expected one of {possible_expected}", possible_expected[0]

    return False, "rule_not_applicable", None


def validate_disjunctive_syllogism(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 2:
        return False, "insufficient_supports", None

    for disjunction_expr, negated_expr in [
        (support_exprs[0], support_exprs[1]),
        (support_exprs[1], support_exprs[0]),
    ]:
        split = split_binary(disjunction_expr, "|")

        if split is None:
            continue

        left, right = split

        if negated_expr == opposite_of(left):
            expected = right

            if claimed == expected:
                return True, "", expected

            return False, f"wrong_derived: expected {expected}", expected

        if negated_expr == opposite_of(right):
            expected = left

            if claimed == expected:
                return True, "", expected

            return False, f"wrong_derived: expected {expected}", expected

    return False, "rule_not_applicable", None


def validate_conjunction_elimination(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 1:
        return False, "insufficient_supports", None

    split = split_binary(support_exprs[0], "&")

    if split is None:
        return False, "rule_not_applicable", None

    left, right = split

    if claimed in {left, right}:
        return True, "", claimed

    return False, f"wrong_derived: expected {left} or {right}", left


def validate_conjunction_introduction(
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if len(support_exprs) != 2:
        return False, "insufficient_supports", None

    left, right = support_exprs

    expected_1 = f"{left} & {right}"
    expected_2 = f"{right} & {left}"

    if claimed in {expected_1, expected_2}:
        return True, "", claimed

    return False, f"wrong_derived: expected {expected_1} or {expected_2}", expected_1


def validate_step_by_rule(
    rule: str,
    support_exprs: List[str],
    claimed: str,
) -> Tuple[bool, str, Optional[str]]:
    if rule == "Modus Ponens":
        return validate_modus_ponens(support_exprs, claimed)

    if rule == "Modus Tollens":
        return validate_modus_tollens(support_exprs, claimed)

    if rule == "Hypothetical Syllogism":
        return validate_hypothetical_syllogism(support_exprs, claimed)

    if rule == "Disjunctive Syllogism":
        return validate_disjunctive_syllogism(support_exprs, claimed)

    if rule == "Conjunction Elimination":
        return validate_conjunction_elimination(support_exprs, claimed)

    if rule == "Conjunction Introduction":
        return validate_conjunction_introduction(support_exprs, claimed)

    raise VerifierError(f"Unsupported rule implementation: {rule}")


def derive_one_step_closure(expressions: Set[str]) -> Set[str]:
    """
    Computes one expansion round of derivable expressions.

    Cycle-safe behavior:
    - Circular conditionals can generate conditionals.
    - Circular conditionals do not generate atomic facts unless an antecedent
      fact is already available.
    - Set-based storage prevents duplicate expressions from expanding forever.
    """

    new_expressions = set(expressions)
    expressions_list = list(expressions)

    # Conjunction Elimination
    for expr in expressions_list:
        split = split_binary(expr, "&")

        if split is not None:
            left, right = split
            new_expressions.add(left)
            new_expressions.add(right)

    # Pairwise rules
    for first in expressions_list:
        for second in expressions_list:
            if first == second:
                continue

            # Modus Ponens and Modus Tollens
            cond = split_binary(first, "->")

            if cond is not None:
                antecedent, consequent = cond

                if second == antecedent:
                    new_expressions.add(consequent)

                if second == opposite_of(consequent):
                    new_expressions.add(opposite_of(antecedent))

            # Hypothetical Syllogism
            first_cond = split_binary(first, "->")
            second_cond = split_binary(second, "->")

            if first_cond is not None and second_cond is not None:
                a, b = first_cond
                c, d = second_cond

                if b == c:
                    new_expressions.add(f"{a} -> {d}")

            # Disjunctive Syllogism
            disjunction = split_binary(first, "|")

            if disjunction is not None:
                left, right = disjunction

                if second == opposite_of(left):
                    new_expressions.add(right)

                if second == opposite_of(right):
                    new_expressions.add(left)

    return new_expressions


def compute_closure(
    symbolic_premises: Dict[str, str],
    max_iterations: int = MAX_CLOSURE_ITERATIONS,
    max_items: int = MAX_CLOSURE_ITEMS,
) -> Tuple[Set[str], Optional[str]]:
    """
    Computes finite closure for final answer checking.

    Safety behavior:
    - Stops when closure reaches a fixed point.
    - Fails if too many iterations are needed.
    - Fails if too many expressions are generated.
    """

    closure = {clean_expr(expr) for expr in symbolic_premises.values()}

    if len(closure) > max_items:
        return closure, "Closure safety limit exceeded. Too many initial expressions."

    for _ in range(max_iterations):
        expanded = derive_one_step_closure(closure)

        if len(expanded) > max_items:
            return expanded, "Closure safety limit exceeded. Possible circular derivation."

        if expanded == closure:
            return closure, None

        closure = expanded

    return closure, "Closure safety iteration limit exceeded. Possible circular derivation."


def verify_special_case(
    answer: str,
    special_case: str,
    target: str,
    symbolic_premises: Dict[str, str],
    closure: Set[str],
) -> Tuple[str, Optional[str], str]:
    """
    Returns:
    - final_answer_check
    - not_entailed_reason
    - validity
    """

    if answer != "not_entailed":
        return "inconsistent", None, "invalid"

    if special_case == SPECIAL_TARGET_NOT_FOUND:
        vocab = premise_vocabulary(symbolic_premises)
        positive_target = strip_negation(target)
        opposite_target = strip_negation(opposite_of(target))

        if positive_target not in vocab and opposite_target not in vocab:
            return "consistent", "target_not_found_in_premises", "valid"

        return "inconsistent", "target_or_opposite_found_in_premise_vocabulary", "invalid"

    if special_case == SPECIAL_NO_DERIVATION_FOUND:
        if target not in closure:
            return "consistent", "no_derivation_found", "valid"

        return "inconsistent", "target_derivable_in_closure", "invalid"

    return "inconsistent", None, "invalid"


def final_answer_check_normal_trace(
    answer: str,
    target: str,
    available_values: Set[str],
) -> Tuple[str, Optional[str]]:
    if answer == "entailed":
        if target in available_values:
            return "consistent", None

        return "inconsistent", None

    if answer == "not_entailed":
        if target in available_values:
            return "inconsistent", "target_derived"

        opposite_target = opposite_of(target)

        if opposite_target in available_values:
            return "consistent", "opposite_derived"

        return "consistent", "target_not_derived_after_valid_steps"

    return "inconsistent", None


def verify_symbolic_trace(
    symbolic_problem: Dict[str, Any],
    symbolic_trace: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verifier component.

    Safety cases handled:
    1. Direct contradiction detection.
    2. Closure safety limits.
    3. Cycle-safe behavior through set-based fixed-point closure.

    Input:
    - symbolic_problem:
      {
          "premises": {"P1": "A -> B", "P2": "A"},
          "target": "B"
      }

    - symbolic_trace:
      {
          "answer": "entailed",
          "steps": [
              {
                  "id": "S1",
                  "derived": "B",
                  "supports": ["P1", "P2"],
                  "rule": "Modus Ponens"
              }
          ],
          "special_case": None
      }

    Output:
    - verification_success: whether the verifier ran successfully
    - verification_result.validity: valid/invalid explanation
    """

    if not isinstance(symbolic_problem, dict):
        return make_failure("Symbolic problem must be a dictionary.")

    if not isinstance(symbolic_trace, dict):
        return make_failure("Symbolic trace must be a dictionary.")

    symbolic_premises = symbolic_problem.get("premises")
    target = symbolic_problem.get("target")

    if not isinstance(symbolic_premises, dict) or not symbolic_premises:
        return make_failure("Symbolic problem is missing premises.")

    if not isinstance(target, str) or not target.strip():
        return make_failure("Symbolic problem is missing target.")

    symbolic_premises = {
        premise_id: clean_expr(expr)
        for premise_id, expr in symbolic_premises.items()
    }

    target = clean_expr(target)

    answer = symbolic_trace.get("answer")
    steps = symbolic_trace.get("steps")
    special_case = symbolic_trace.get("special_case")

    if answer not in {"entailed", "not_entailed"}:
        return make_failure("Symbolic trace has invalid answer value.")

    if not isinstance(steps, list):
        return make_failure("Symbolic trace steps must be a list.")

    # ==================================================
    # Closure computation with safety limits
    # ==================================================
    closure, closure_error = compute_closure(symbolic_premises)

    if closure_error is not None:
        return make_failure(closure_error)

    # ==================================================
    # Contradiction detection
    # ==================================================
    contradiction = find_direct_contradiction(closure)

    if contradiction is not None:
        positive, negative = contradiction

        return make_failure(
            f"Contradictory premises detected: {positive} and {negative}."
        )

    # ==================================================
    # Special cases
    # ==================================================
    if special_case is not None:
        if steps:
            return make_failure("Special-case traces must not contain normal steps.")

        if special_case not in {SPECIAL_TARGET_NOT_FOUND, SPECIAL_NO_DERIVATION_FOUND}:
            return make_failure(f"Unsupported special case: {special_case}")

        final_check, reason, validity = verify_special_case(
            answer=answer,
            special_case=special_case,
            target=target,
            symbolic_premises=symbolic_premises,
            closure=closure,
        )

        return make_success(
            {
                "validity": validity,
                "step_results": [],
                "final_answer_check": final_check,
                "not_entailed_reason": reason,
                "available_knowledge": dict(symbolic_premises),
                "closure": sorted(closure),
            }
        )

    # ==================================================
    # Normal trace verification
    # ==================================================
    available_knowledge = dict(symbolic_premises)
    step_results = []

    all_steps_valid = True

    for step in steps:
        step_id = step.get("id")
        claimed_derived = step.get("derived")
        supports = step.get("supports")
        rule = step.get("rule")

        if not isinstance(step_id, str) or not re.match(r"^S\d+$", step_id):
            return make_failure(f"Invalid step id: {step_id}")

        if not isinstance(claimed_derived, str) or not claimed_derived.strip():
            return make_failure(f"Missing derived expression in step {step_id}.")

        if not isinstance(supports, list) or not supports:
            return make_failure(f"Missing supports in step {step_id}.")

        if not isinstance(rule, str) or not rule.strip():
            return make_failure(f"Missing rule in step {step_id}.")

        claimed_derived = clean_expr(claimed_derived)

        if rule not in SUPPORTED_RULES:
            return make_failure(f"Unsupported rule implementation: {rule}")

        support_exprs, support_error = get_support_expressions(
            supports=supports,
            available_knowledge=available_knowledge,
        )

        if support_error is not None:
            all_steps_valid = False

            step_results.append(
                {
                    "id": step_id,
                    "valid": False,
                    "error": support_error,
                    "derived": claimed_derived,
                    "expected": None,
                }
            )

            continue

        try:
            is_valid, error, expected = validate_step_by_rule(
                rule=rule,
                support_exprs=support_exprs,
                claimed=claimed_derived,
            )
        except VerifierError as e:
            return make_failure(str(e))

        if is_valid:
            available_knowledge[step_id] = claimed_derived

            step_results.append(
                {
                    "id": step_id,
                    "valid": True,
                    "error": None,
                    "derived": claimed_derived,
                    "expected": expected,
                }
            )
        else:
            all_steps_valid = False

            step_results.append(
                {
                    "id": step_id,
                    "valid": False,
                    "error": error,
                    "derived": claimed_derived,
                    "expected": expected,
                }
            )

    available_values = set(available_knowledge.values())

    final_check, not_entailed_reason = final_answer_check_normal_trace(
        answer=answer,
        target=target,
        available_values=available_values,
    )

    validity = "valid" if all_steps_valid and final_check == "consistent" else "invalid"

    return make_success(
        {
            "validity": validity,
            "step_results": step_results,
            "final_answer_check": final_check,
            "not_entailed_reason": not_entailed_reason,
            "available_knowledge": available_knowledge,
            "closure": sorted(closure),
        }
    )