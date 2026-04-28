from typing import Dict, Any


def parse_normalized_prompt(normalized_text: str) -> Dict[str, Any]:
    if not normalized_text or not normalized_text.strip():
        return {
            "prompt_parse_success": False,
            "prompt_parse_error": "Empty normalized prompt.",
            "problem": None,
        }

    lines = [line.rstrip() for line in normalized_text.splitlines()]

    premises_started = False
    question_started = False
    premises = []
    question = None

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        if line == "Premises:":
            if premises_started:
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": "Duplicate Premises section.",
                    "problem": None,
                }
            premises_started = True
            continue

        if line == "Question:":
            if question_started:
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": "Duplicate Question section.",
                    "problem": None,
                }
            question_started = True
            continue

        if question_started:
            if question is not None:
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": "Multiple question lines found.",
                    "problem": None,
                }
            question = line
            continue

        if premises_started:
            if "." not in line:
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": f"Malformed premise line: '{line}'",
                    "problem": None,
                }

            prefix, content = line.split(".", 1)
            if not prefix.isdigit():
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": f"Invalid premise numbering: '{line}'",
                    "problem": None,
                }

            content = content.strip()
            if not content:
                return {
                    "prompt_parse_success": False,
                    "prompt_parse_error": f"Empty premise content in line: '{line}'",
                    "problem": None,
                }

            premises.append(content)
            continue

        return {
            "prompt_parse_success": False,
            "prompt_parse_error": f"Unexpected content before sections: '{line}'",
            "problem": None,
        }

    if not premises_started:
        return {
            "prompt_parse_success": False,
            "prompt_parse_error": "Missing Premises section.",
            "problem": None,
        }

    if not premises:
        return {
            "prompt_parse_success": False,
            "prompt_parse_error": "No premises found.",
            "problem": None,
        }

    if not question_started:
        return {
            "prompt_parse_success": False,
            "prompt_parse_error": "Missing Question section.",
            "problem": None,
        }

    if question is None or not question.strip():
        return {
            "prompt_parse_success": False,
            "prompt_parse_error": "Missing question content.",
            "problem": None,
        }

    problem = {
        "premises": {f"P{i+1}": premise for i, premise in enumerate(premises)},
        "question": question,
    }

    return {
        "prompt_parse_success": True,
        "prompt_parse_error": None,
        "problem": problem,
    }

import re
from typing import Dict, Any


def parse_llm_response(raw_output: str) -> Dict[str, Any]:
    if not raw_output or not raw_output.strip():
        return {
            "response_parse_success": False,
            "response_parse_error": "Empty LLM output.",
            "trace": None,
        }

    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]

    if not lines or not lines[0].startswith("Answer:"):
        return {
            "response_parse_success": False,
            "response_parse_error": "Missing or malformed 'Answer:' line.",
            "trace": None,
        }

    answer = lines[0].replace("Answer:", "").strip()
    if answer not in {"entailed", "not_entailed"}:
        return {
            "response_parse_success": False,
            "response_parse_error": "Answer must be 'entailed' or 'not_entailed'.",
            "trace": None,
        }

    if len(lines) < 2 or lines[1] != "Steps:":
        return {
            "response_parse_success": False,
            "response_parse_error": "Missing 'Steps:' line.",
            "trace": None,
        }

    step_lines = lines[2:]

    if not step_lines:
        return {
            "response_parse_success": False,
            "response_parse_error": "No steps found after 'Steps:'.",
            "trace": None,
        }

    # Special case: Target Not Found in Premises
    if len(step_lines) == 1 and step_lines[0] == "Target Not Found in Premises":
        return {
            "response_parse_success": True,
            "response_parse_error": None,
            "trace": {
                "answer": answer,
                "steps": [],
                "special_case": "Target Not Found in Premises",
            },
        }

    step_pattern = re.compile(
        r"^(S\d+):\s+(.*?)\s+\[from:\s+([^\]]+)\]\s+\[rule:\s+([^\]]+)\]$"
    )

    parsed_steps = []

    for line in step_lines:
        match = step_pattern.match(line)
        if not match:
            return {
                "response_parse_success": False,
                "response_parse_error": f"Malformed step format: '{line}'",
                "trace": None,
            }

        step_id = match.group(1).strip()
        statement = match.group(2).strip()
        supports_raw = match.group(3).strip()
        rule = match.group(4).strip()

        supports = [s.strip() for s in supports_raw.split(",") if s.strip()]

        if not statement:
            return {
                "response_parse_success": False,
                "response_parse_error": f"Empty statement in {step_id}.",
                "trace": None,
            }

        if not supports:
            return {
                "response_parse_success": False,
                "response_parse_error": f"No supports found in {step_id}.",
                "trace": None,
            }

        if not rule:
            return {
                "response_parse_success": False,
                "response_parse_error": f"No rule found in {step_id}.",
                "trace": None,
            }

        parsed_steps.append(
            {
                "id": step_id,
                "statement": statement,
                "supports": supports,
                "rule": rule,
            }
        )

    return {
        "response_parse_success": True,
        "response_parse_error": None,
        "trace": {
            "answer": answer,
            "steps": parsed_steps,
            "special_case": None,
        },
    }