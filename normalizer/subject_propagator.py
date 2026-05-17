import re


def propagate_plural_subject_in_conditional(sentence: str) -> str:
    s = sentence.strip().rstrip(".")

    parts = re.split(r",\s*then\s*", s, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return sentence

    left, consequent = parts[0].strip(), parts[1].strip()

    if not left.lower().startswith("if "):
        return sentence

    antecedent = left[3:].strip()
    ant_words = antecedent.split()

    if not ant_words:
        return sentence

    subject = ant_words[0]

    if consequent.lower().startswith("they "):
        rest = consequent.split(maxsplit=1)[1] if len(consequent.split()) > 1 else ""
        consequent = f"{subject} {rest}".strip()

    return f"If {antecedent}, then {consequent}."
