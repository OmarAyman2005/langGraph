from typing import Dict, Optional


DEFAULT_REPAIR_HINT = (
    "Please rewrite the input using the supported project format: "
    "one or more simple English premises followed by one clear yes/no question."
)


REPAIR_HINTS: Dict[str, str] = {
    # ==================================================
    # Normalizer errors
    # ==================================================
    "Empty input": (
        "Please enter at least one premise and one yes/no question."
    ),
    "No yes/no question detected": (
        "Please add one clear yes/no question at the end of the prompt, ending with a question mark."
    ),
    "No candidate premises found": (
        "Please add at least one premise before the question."
    ),
    "One or more premises do not map into supported sentence patterns": (
        "Please rewrite the premise(s) using supported simple forms, such as: "
        "'Ahmed studies.', 'if Ahmed studies, then Ahmed passes.', "
        "'Ahmed studies and Sara sleeps.', or 'Ahmed studies or Sara sleeps.'."
    ),
    "Question target does not map into a supported atomic proposition": (
        "Please rewrite the question as a simple yes/no atomic question, such as "
        "'Does Ahmed study?' or 'Is the door open?'."
    ),
    "Question section appears before Premises section": (
        "Please provide premises first, then one yes/no question at the end."
    ),
    "Missing Question section": (
        "Please add one question after the premises."
    ),
    "Missing Premises section": (
        "Please add at least one premise before the question."
    ),

    # ==================================================
    # Parser 1 errors
    # ==================================================
    "No premises found": (
        "Please include at least one valid premise before the question."
    ),
    "Missing question content": (
        "Please write a clear yes/no question after the premises."
    ),
    "Multiple question lines found": (
        "Please include only one final yes/no question."
    ),
    "Malformed premise line": (
        "Please make sure each premise is well-formed and can be normalized correctly."
    ),
    "Invalid premise numbering": (
        "Please make sure premise numbering is sequential, starting from 1."
    ),
    "Premise is not in a normalized recoverable form": (
        "Please rewrite the premise using a supported simple sentence pattern."
    ),
    "Question is not in a normalized recoverable form": (
        "Please rewrite the question as a supported yes/no atomic question."
    ),

    # ==================================================
    # LLM / Parser 2 errors
    # ==================================================
    "LLM response generation failed": (
        "The LLM response could not be generated. Please try again with a simpler prompt."
    ),
    "LLM returned an empty response": (
        "The LLM returned an empty response. Please try again with a simpler prompt."
    ),
    "Missing or malformed Answer line": (
        "The generated explanation did not follow the required answer format. Please retry the prompt."
    ),
    "Missing or malformed Steps section": (
        "The generated explanation did not include a valid Steps section. Please retry the prompt."
    ),
    "Malformed step format": (
        "The generated explanation had an invalid step format. Please retry the prompt."
    ),
    "Unsupported rule": (
        "The generated explanation used an unsupported rule. Please retry the prompt."
    ),

    # ==================================================
    # Translator errors
    # ==================================================
    "Unsupported sentence pattern": (
        "Please rewrite the input using only supported simple sentence patterns."
    ),
    "Unsupported question pattern": (
        "Please rewrite the question as a supported yes/no atomic question."
    ),

    # ==================================================
    # Verifier danger cases
    # ==================================================
    "Contradictory premises detected": (
        "Please remove or revise one of the contradictory premises. "
        "The verifier does not process inconsistent premise sets."
    ),
    "Closure safety limit exceeded": (
        "The reasoning structure appears too cyclic or too large. "
        "Please simplify the premises and avoid excessive circular implication chains."
    ),
    "Closure safety iteration limit exceeded": (
        "The reasoning structure appears cyclic. Please simplify the premises."
    ),
}


def find_repair_hint(error_message: Optional[str]) -> str:
    """
    Maps a pipeline error message to a predefined user repair hint.
    """

    if not error_message:
        return DEFAULT_REPAIR_HINT

    for known_error, hint in REPAIR_HINTS.items():
        if known_error.lower() in error_message.lower():
            return hint

    return DEFAULT_REPAIR_HINT


def build_repair_message(
    error_component: Optional[str],
    error_message: Optional[str],
    repair_attempt: int,
    max_repair_attempts: int,
) -> str:
    """
    Builds a clear repair message for the user.
    """

    hint = find_repair_hint(error_message)

    component_name = error_component or "unknown component"
    error_text = error_message or "Unknown error."

    return (
        f"Pipeline failed at: {component_name}\n"
        f"Error: {error_text}\n\n"
        f"Repair instruction:\n"
        f"{hint}\n\n"
        f"Repair attempt {repair_attempt}/{max_repair_attempts}.\n"
        f"Please re-enter the corrected raw prompt."
    )