import re
from typing import Any, Dict, List, Optional, Tuple

from normalizer.question_pattern_matcher import question_to_target_candidates


UNSUPPORTED_ATOM_KEYWORDS = {
    "all",
    "every",
    "some",
    "any",
    "none",
    "probably",
    "maybe",
    "possibly",
    "because",
    "unless",
    "although",
    "however",
    "than",
}


class TranslationError(Exception):
    pass


class PropositionSymbolTable:
    """
    Maintains a consistent mapping from normalized English atomic propositions
    to symbolic labels.

    Example:
    "it rains." -> ItRains
    "the ground is wet." -> GroundIsWet
    "not the ground is wet." -> ~GroundIsWet
    """

    def __init__(self) -> None:
        self.atom_to_symbol: Dict[str, str] = {}

    def get_or_create_symbol(self, atom_text: str) -> str:
        canonical_atom = canonicalize_atom_text(atom_text)

        if canonical_atom not in self.atom_to_symbol:
            self.atom_to_symbol[canonical_atom] = make_symbol_label(canonical_atom)

        return self.atom_to_symbol[canonical_atom]

    def as_dict(self) -> Dict[str, str]:
        return dict(self.atom_to_symbol)


def make_failure(
    error: str,
    symbolic_problem: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "translation_success": False,
        "translation_error": error,
        "symbolic_problem": symbolic_problem,
        "symbolic_trace": None,
    }


def make_success(
    symbolic_problem: Dict[str, Any],
    symbolic_trace: Dict[str, Any],
    proposition_map: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "translation_success": True,
        "translation_error": None,
        "symbolic_problem": symbolic_problem,
        "symbolic_trace": symbolic_trace,
        "proposition_map": proposition_map,
    }


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def strip_final_punctuation(text: str) -> str:
    return clean_text(text).rstrip(".?").strip()


def inflect_simple_present_for_does(verb_phrase: str) -> str:
    """
    Converts a base verb phrase after 'does' into the normalized simple-present
    form used by the Normalizer.

    Examples:
    pass -> passes
    study -> studies
    sleep -> sleeps
    play football -> plays football
    """

    phrase = clean_text(verb_phrase.lower())

    if not phrase:
        return phrase

    words = phrase.split()
    verb = words[0]
    rest = words[1:]

    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        verb = verb[:-1] + "ies"
    elif verb.endswith(("s", "sh", "ch", "x", "z", "o")):
        verb = verb + "es"
    else:
        verb = verb + "s"

    return " ".join([verb] + rest)


def normalize_internal_negation_literal(text: str) -> str:
    """
    Converts internal negative forms into the project's canonical negation form.

    Examples:
    ahmed not passes        -> not ahmed passes
    ahmed does not pass     -> not ahmed passes
    they do not play        -> not they play
    ahmed did not win       -> not ahmed did win

    This is especially important for negative yes/no questions such as:
    does ahmed not pass?
    """

    cleaned = strip_final_punctuation(text).lower()

    if cleaned.startswith("not "):
        return cleaned

    # Example produced by question_to_target_candidates:
    # ahmed not passes -> not ahmed passes
    if " not " in cleaned and not re.search(r"\b(do|does|did)\s+not\b", cleaned):
        return "not " + cleaned.replace(" not ", " ", 1)

    # do/does/did not forms.
    match = re.match(r"^(.+?)\s+(do|does|did)\s+not\s+(.+)$", cleaned)

    if match:
        subject = clean_text(match.group(1))
        auxiliary = match.group(2)
        predicate = clean_text(match.group(3))

        if auxiliary == "does":
            predicate = inflect_simple_present_for_does(predicate)
            return f"not {subject} {predicate}"

        if auxiliary == "do":
            return f"not {subject} {predicate}"

        # For did, preserve did-support because tense is meaningful in the
        # current Normalizer design.
        return f"not {subject} did {predicate}"

    return cleaned


def canonicalize_atom_text(atom_text: str) -> str:
    atom = strip_final_punctuation(atom_text).lower()

    if not atom:
        raise TranslationError("Empty atomic proposition.")

    if atom.startswith("not "):
        raise TranslationError(
            f"Negated expression passed where atomic proposition was expected: '{atom_text}'"
        )

    if atom.startswith("if "):
        raise TranslationError(
            f"Conditional expression passed where atomic proposition was expected: '{atom_text}'"
        )

    if ", then " in atom:
        raise TranslationError(
            f"Conditional expression passed where atomic proposition was expected: '{atom_text}'"
        )

    if " and " in atom:
        raise TranslationError(
            f"Conjunction expression passed where atomic proposition was expected: '{atom_text}'"
        )

    if " or " in atom:
        raise TranslationError(
            f"Disjunction expression passed where atomic proposition was expected: '{atom_text}'"
        )

    words = re.findall(r"[a-zA-Z]+", atom)

    if not words:
        raise TranslationError(f"Cannot translate atomic proposition: '{atom_text}'")

    for word in words:
        if word in UNSUPPORTED_ATOM_KEYWORDS:
            raise TranslationError(
                f"Unsupported atomic proposition pattern: '{atom_text}'"
            )

    return atom


def make_symbol_label(atom_text: str) -> str:
    """
    Converts an English atom to a deterministic symbolic label.

    Examples:
    it rains -> ItRains
    the ground is wet -> GroundIsWet
    ahmed passes -> AhmedPasses
    """

    canonical_atom = canonicalize_atom_text(atom_text)
    words = re.findall(r"[a-zA-Z]+", canonical_atom)

    # Remove only leading articles to make symbols cleaner.
    if words and words[0] in {"the", "a", "an"}:
        words = words[1:]

    if not words:
        raise TranslationError(f"Cannot create symbol label from: '{atom_text}'")

    return "".join(word.capitalize() for word in words)


def split_top_level_once(text: str, connector: str) -> Optional[Tuple[str, str]]:
    """
    Splits on the first occurrence of a binary connector.

    This project uses a restricted grammar, so no nested parsing is needed here.
    """

    pattern = rf"\s+{re.escape(connector)}\s+"
    parts = re.split(pattern, text, maxsplit=1)

    if len(parts) != 2:
        return None

    left = clean_text(parts[0])
    right = clean_text(parts[1])

    if not left or not right:
        return None

    return left, right


def translate_literal(text: str, symbol_table: PropositionSymbolTable) -> str:
    """
    Translates an atom or negated atom.

    x       -> X
    not x   -> ~X
    """

    cleaned = normalize_internal_negation_literal(text)

    if not cleaned:
        raise TranslationError("Empty literal.")

    if cleaned.startswith("not "):
        inner = cleaned[4:].strip()

        if not inner:
            raise TranslationError(f"Malformed negation: '{text}'")

        if inner.startswith("(") or inner.startswith("if "):
            raise TranslationError(f"Unsupported negated expression: '{text}'")

        return f"~{symbol_table.get_or_create_symbol(inner)}"

    return symbol_table.get_or_create_symbol(cleaned)


def translate_statement(statement: str, symbol_table: PropositionSymbolTable) -> str:
    """
    Translates a normalized English logical statement into a symbolic expression.

    Supported:
    - atom
    - not atom
    - if atom/literal, then atom/literal
    - atom/literal and atom/literal
    - atom/literal or atom/literal
    """

    if not isinstance(statement, str) or not statement.strip():
        raise TranslationError("Empty statement.")

    s = strip_final_punctuation(statement).lower()

    # ==================================================
    # Conditional
    # ==================================================
    if s.startswith("if ") and ", then " in s:
        body = s[3:].strip()
        parts = re.split(r",\s*then\s+", body, maxsplit=1)

        if len(parts) != 2:
            raise TranslationError(f"Malformed conditional: '{statement}'")

        antecedent = clean_text(parts[0])
        consequent = clean_text(parts[1])

        left_symbol = translate_literal(antecedent, symbol_table)
        right_symbol = translate_literal(consequent, symbol_table)

        return f"{left_symbol} -> {right_symbol}"

    # Reject malformed conditionals.
    if s.startswith("if ") or ", then " in s:
        raise TranslationError(f"Malformed conditional: '{statement}'")

    # ==================================================
    # Conjunction
    # ==================================================
    conjunction_parts = split_top_level_once(s, "and")

    if conjunction_parts is not None:
        left, right = conjunction_parts
        left_symbol = translate_literal(left, symbol_table)
        right_symbol = translate_literal(right, symbol_table)

        return f"{left_symbol} & {right_symbol}"

    # ==================================================
    # Disjunction
    # ==================================================
    disjunction_parts = split_top_level_once(s, "or")

    if disjunction_parts is not None:
        left, right = disjunction_parts
        left_symbol = translate_literal(left, symbol_table)
        right_symbol = translate_literal(right, symbol_table)

        return f"{left_symbol} | {right_symbol}"

    # ==================================================
    # Literal
    # ==================================================
    return translate_literal(s, symbol_table)


def translate_question(question: str, symbol_table: PropositionSymbolTable) -> str:
    """
    Translates a normalized yes/no question into a symbolic target.

    Examples:
    does ahmed pass?       -> AhmedPasses
    is the ground wet?     -> GroundIsWet
    is the door not open?  -> ~DoorIsOpen
    does ahmed not pass?   -> ~AhmedPasses
    """

    if not isinstance(question, str) or not question.strip():
        raise TranslationError("Empty question.")

    target_candidates = question_to_target_candidates(question)

    if not target_candidates:
        raise TranslationError(f"Unsupported question form: '{question}'")

    primary_target = target_candidates[0]
    normalized_target = normalize_internal_negation_literal(primary_target)

    return translate_statement(normalized_target, symbol_table)


def translate_problem(
    parsed_problem: Dict[str, Any],
    symbol_table: PropositionSymbolTable,
) -> Dict[str, Any]:
    if not isinstance(parsed_problem, dict):
        raise TranslationError("Parsed problem must be a dictionary.")

    premises = parsed_problem.get("premises")
    question = parsed_problem.get("question")

    if not isinstance(premises, dict) or not premises:
        raise TranslationError("Parsed problem is missing premises.")

    if not isinstance(question, str) or not question.strip():
        raise TranslationError("Parsed problem is missing question.")

    symbolic_premises = {}

    for premise_id, premise_text in premises.items():
        if not re.match(r"^P\d+$", premise_id):
            raise TranslationError(f"Invalid premise id: '{premise_id}'")

        try:
            symbolic_premises[premise_id] = translate_statement(
                premise_text,
                symbol_table,
            )
        except TranslationError as e:
            raise TranslationError(
                f"Unsupported sentence pattern in premise {premise_id}: "
                f"'{premise_text}'. {e}"
            )

    try:
        symbolic_target = translate_question(question, symbol_table)
    except TranslationError as e:
        raise TranslationError(
            f"Unsupported question pattern: '{question}'. {e}"
        )

    return {
        "premises": symbolic_premises,
        "target": symbolic_target,
    }


def translate_trace(
    parsed_trace: Dict[str, Any],
    symbol_table: PropositionSymbolTable,
) -> Dict[str, Any]:
    if not isinstance(parsed_trace, dict):
        raise TranslationError("Parsed trace must be a dictionary.")

    answer = parsed_trace.get("answer")
    steps = parsed_trace.get("steps")
    special_case = parsed_trace.get("special_case")

    if answer not in {"entailed", "not_entailed"}:
        raise TranslationError("Parsed trace has invalid answer value.")

    if special_case == "Target Not Found in Premises":
        return {
            "answer": answer,
            "steps": [],
            "special_case": special_case,
        }

    if special_case is not None:
        raise TranslationError(f"Unsupported special case: '{special_case}'")

    if not isinstance(steps, list):
        raise TranslationError("Parsed trace steps must be a list.")

    symbolic_steps = []

    for step in steps:
        step_id = step.get("id")
        statement = step.get("statement")
        supports = step.get("supports")
        rule = step.get("rule")

        if not isinstance(step_id, str) or not re.match(r"^S\d+$", step_id):
            raise TranslationError(f"Invalid step id: '{step_id}'")

        if not isinstance(statement, str) or not statement.strip():
            raise TranslationError(f"Missing statement in step {step_id}.")

        if not isinstance(supports, list) or not supports:
            raise TranslationError(f"Missing supports in step {step_id}.")

        if not isinstance(rule, str) or not rule.strip():
            raise TranslationError(f"Missing rule in step {step_id}.")

        try:
            derived = translate_statement(statement, symbol_table)
        except TranslationError as e:
            raise TranslationError(
                f"Unsupported sentence pattern in step {step_id}: "
                f"'{statement}'. {e}"
            )

        symbolic_steps.append(
            {
                "id": step_id,
                "derived": derived,
                "supports": supports,
                "rule": rule,
            }
        )

    return {
        "answer": answer,
        "steps": symbolic_steps,
        "special_case": special_case,
    }


def translate_problem_and_trace(
    parsed_problem: Dict[str, Any],
    parsed_trace: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Translator component.

    Input:
    - parsed problem object from Parser 1
    - parsed trace object from Parser 2

    Output:
    - symbolic problem
    - symbolic trace
    - proposition map

    This component performs only translation.
    Logical correctness is handled later by the Verifier.
    """

    if not parsed_problem:
        return make_failure("Missing parsed problem.")

    if not parsed_trace:
        return make_failure("Missing parsed trace.")

    symbol_table = PropositionSymbolTable()

    symbolic_problem = None

    try:
        symbolic_problem = translate_problem(parsed_problem, symbol_table)
    except TranslationError as e:
        return make_failure(str(e), symbolic_problem=None)

    try:
        symbolic_trace = translate_trace(parsed_trace, symbol_table)
    except TranslationError as e:
        return make_failure(str(e), symbolic_problem=symbolic_problem)

    return make_success(
        symbolic_problem=symbolic_problem,
        symbolic_trace=symbolic_trace,
        proposition_map=symbol_table.as_dict(),
    )