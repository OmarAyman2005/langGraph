import re
from typing import Any, Dict, List


ALLOWED_ANSWERS = {"entailed", "not_entailed"}

ALLOWED_RULES = {
    "Modus Ponens",
    "Modus Tollens",
    "Hypothetical Syllogism",
    "Disjunctive Syllogism",
    "Conjunction Introduction",
    "Conjunction Elimination",
}

SPECIAL_TARGET_NOT_FOUND = "Target Not Found in Premises"


def _make_failure(error: str) -> Dict[str, Any]:
    return {
        "response_parse_success": False,
        "response_parse_error": error,
        "trace": None,
    }


def _make_success(
    answer: str,
    steps: List[Dict[str, Any]],
    special_case: str | None = None,
) -> Dict[str, Any]:
    return {
        "response_parse_success": True,
        "response_parse_error": None,
        "trace": {
            "answer": answer,
            "steps": steps,
            "special_case": special_case,
        },
    }


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _parse_answer_line(line: str) -> str | None:
    if not line.startswith("Answer:"):
        return None

    answer = line.replace("Answer:", "", 1).strip()

    if answer not in ALLOWED_ANSWERS:
        return None

    return answer


def _parse_supports(supports_raw: str) -> List[str]:
    return [
        support.strip()
        for support in supports_raw.split(",")
        if support.strip()
    ]


def _validate_supports(
    step_id: str,
    supports: List[str],
    current_step_number: int,
) -> str | None:
    if not supports:
        return f"No supports found in {step_id}."

    for support in supports:
        if not re.match(r"^(P\d+|S\d+)$", support):
            return f"Invalid support reference in {step_id}: '{support}'."

        if support.startswith("S"):
            support_number = int(support[1:])

            if support_number >= current_step_number:
                return (
                    f"Invalid support reference in {step_id}: "
                    f"'{support}' must refer only to an earlier step."
                )

    return None


def parse_llm_response(raw_output: str) -> Dict[str, Any]:
    """
    Parser 2: LLM Response Parser.

    Input example:
    Answer: entailed
    Steps:
    S1: the ground is wet. [from: P1, P2] [rule: Modus Ponens]

    Responsibilities:
    1. Read and validate the Answer line.
    2. Validate that answer is one of: entailed, not_entailed.
    3. Read the Steps section.
    4. Parse each step into:
       - id
       - statement
       - supports
       - rule
    5. Validate schema compliance:
       - Answer line exists.
       - Steps section exists.
       - Each step has all required parts.
       - Step IDs are sequential: S1, S2, S3, ...
       - Support references are syntactically well-formed.
       - Step supports only refer to premises or earlier steps.
       - Rule names are supported.
    6. Support the special not-entailed case:
       Target Not Found in Premises

    Notes:
    - This parser validates format/schema only.
    - Logical correctness is left for the Translator + Verifier.
    """

    if not isinstance(raw_output, str) or not raw_output.strip():
        return _make_failure("Empty LLM output.")

    if "```" in raw_output:
        return _make_failure("LLM output must not contain markdown/code fences.")

    lines = [
        _clean_line(line)
        for line in raw_output.splitlines()
        if line.strip()
    ]

    if not lines:
        return _make_failure("Empty LLM output.")

    # ==================================================
    # Answer line
    # ==================================================
    answer = _parse_answer_line(lines[0])

    if answer is None:
        return _make_failure("Missing or malformed Answer line.")

    # ==================================================
    # Steps section
    # ==================================================
    if len(lines) < 2:
        return _make_failure("Missing Steps section.")

    if lines[1] != "Steps:":
        return _make_failure("Missing or malformed Steps section.")

    step_lines = lines[2:]

    if not step_lines:
        return _make_failure("No steps found after Steps section.")

    # ==================================================
    # Special case: Target Not Found in Premises
    # ==================================================
    if len(step_lines) == 1 and step_lines[0] == SPECIAL_TARGET_NOT_FOUND:
        if answer != "not_entailed":
            return _make_failure(
                "Target Not Found in Premises can only be used with answer not_entailed."
            )

        return _make_success(
            answer=answer,
            steps=[],
            special_case=SPECIAL_TARGET_NOT_FOUND,
        )

    if SPECIAL_TARGET_NOT_FOUND in step_lines:
        return _make_failure(
            "Target Not Found in Premises must appear alone as the only step."
        )

    # ==================================================
    # Normal reasoning steps
    # ==================================================
    step_pattern = re.compile(
        r"^(S\d+):\s+(.+?)\s+\[from:?\s+([^\]]+)\]\s+\[rule:?\s+([^\]]+)\]$"
    )

    parsed_steps = []
    expected_step_number = 1

    for line in step_lines:
        if line.startswith("Answer:"):
            return _make_failure("Duplicate or misplaced Answer line found.")

        if line == "Steps:":
            return _make_failure("Duplicate Steps section found.")

        match = step_pattern.match(line)

        if not match:
            return _make_failure(f"Malformed step format: '{line}'")

        step_id = match.group(1).strip()
        statement = match.group(2).strip()
        supports_raw = match.group(3).strip()
        rule = match.group(4).strip()

        expected_step_id = f"S{expected_step_number}"

        if step_id != expected_step_id:
            return _make_failure(
                f"Invalid step numbering: expected {expected_step_id}, got {step_id}."
            )

        if not statement:
            return _make_failure(f"Empty statement in {step_id}.")

        if statement != statement.lower():
            return _make_failure(f"Statement in {step_id} must be lowercase.")

        if not statement.endswith("."):
            return _make_failure(f"Statement in {step_id} must end with a period.")

        supports = _parse_supports(supports_raw)

        support_error = _validate_supports(
            step_id=step_id,
            supports=supports,
            current_step_number=expected_step_number,
        )

        if support_error is not None:
            return _make_failure(support_error)

        if not rule:
            return _make_failure(f"Missing rule in {step_id}.")

        if rule not in ALLOWED_RULES:
            return _make_failure(f"Unsupported rule in {step_id}: '{rule}'.")

        parsed_steps.append(
            {
                "id": step_id,
                "statement": statement,
                "supports": supports,
                "rule": rule,
            }
        )

        expected_step_number += 1

    return _make_success(
        answer=answer,
        steps=parsed_steps,
        special_case=None,
    )