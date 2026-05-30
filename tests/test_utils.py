import json
from typing import Any


def pretty_json(data: Any) -> str:
    """
    Converts dictionaries/lists into readable JSON-like output.

    Used only for test/debug printing.
    Does not affect pipeline objects internally.
    """
    return json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
    )


def print_pretty_json(title: str, data: Any) -> None:
    print(title)
    print(pretty_json(data))