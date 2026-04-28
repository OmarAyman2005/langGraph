import re
from typing import Dict, Any, Optional


def normalize_atom(text: str) -> str:
    text = text.strip().rstrip(".?")

    lowered = text.lower()

    # Very small controlled normalization for v1
    replacements = {
        "it rains": "ItRains",
        "the ground gets wet": "GroundGetsWet",
        "the ground is wet": "GroundIsWet",
        "ahmed is happy": "AhmedIsHappy",
    }

    if lowered in replacements:
        return replacements[lowered]

    # fallback generic camel-style normalization
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        raise ValueError(f"Cannot normalize atom: '{text}'")

    return "".join(word.capitalize() for word in words)


def question_to_atom(question: str) -> str:
    q = question.strip().rstrip("?")

    lowered = q.lower()

    mapping = {
        "does the ground get wet": "GroundGetsWet",
        "is ahmed happy": "AhmedIsHappy",
        "does it rain": "ItRains",
    }

    if lowered in mapping:
        return mapping[lowered]

    # basic fallback patterns
    if lowered.startswith("does "):
        rest = q[5:].strip()
        return normalize_atom(rest)

    if lowered.startswith("is "):
        rest = q[3:].strip()
        return normalize_atom(rest)

    if lowered.startswith("has "):
        rest = q[4:].strip()
        return normalize_atom(rest)

    if lowered.startswith("will "):
        rest = q[5:].strip()
        return normalize_atom(rest)

    raise ValueError(f"Unsupported question form: '{question}'")


def statement_to_symbol(statement: str) -> str:
    s = statement.strip().rstrip(".")

    lowered = s.lower()

    # Conditional
    if lowered.startswith("if ") and ", then " in lowered:
        parts = re.split(r",\s*then\s*", s, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Malformed conditional: '{statement}'")

        left = parts[0][3:].strip()  # remove "If "
        right = parts[1].strip()

        return f"{normalize_atom(left)} -> {normalize_atom(right)}"

    # Disjunction
    if " or " in lowered:
        parts = re.split(r"\s+or\s+", s, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Malformed disjunction: '{statement}'")
        return f"{normalize_atom(parts[0])} | {normalize_atom(parts[1])}"

    # Conjunction
    if " and " in lowered:
        parts = re.split(r"\s+and\s+", s, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            raise ValueError(f"Malformed conjunction: '{statement}'")
        return f"{normalize_atom(parts[0])} & {normalize_atom(parts[1])}"

    # Negation
    if lowered.startswith("not "):
        inner = s[4:].strip()
        return f"~{normalize_atom(inner)}"

    # Fact
    return normalize_atom(s)


def translate_problem_and_trace(
    parsed_problem: Dict[str, Any],
    parsed_trace: Dict[str, Any],
) -> Dict[str, Any]:
    if not parsed_problem:
        return {
            "translation_success": False,
            "translation_error": "Missing parsed problem.",
            "symbolic_problem": None,
            "symbolic_trace": None,
        }

    if not parsed_trace:
        return {
            "translation_success": False,
            "translation_error": "Missing parsed trace.",
            "symbolic_problem": None,
            "symbolic_trace": None,
        }

    try:
        symbolic_premises = {
            pid: statement_to_symbol(text)
            for pid, text in parsed_problem["premises"].items()
        }

        symbolic_target = question_to_atom(parsed_problem["question"])

        symbolic_steps = []
        for step in parsed_trace.get("steps", []):
            symbolic_steps.append(
                {
                    "id": step["id"],
                    "derived": statement_to_symbol(step["statement"]),
                    "supports": step["supports"],
                    "rule": step["rule"],
                }
            )

        symbolic_problem = {
            "premises": symbolic_premises,
            "target": symbolic_target,
        }

        symbolic_trace = {
            "answer": parsed_trace["answer"],
            "steps": symbolic_steps,
            "special_case": parsed_trace.get("special_case"),
        }

        return {
            "translation_success": True,
            "translation_error": None,
            "symbolic_problem": symbolic_problem,
            "symbolic_trace": symbolic_trace,
        }

    except Exception as e:
        return {
            "translation_success": False,
            "translation_error": str(e),
            "symbolic_problem": None,
            "symbolic_trace": None,
        }