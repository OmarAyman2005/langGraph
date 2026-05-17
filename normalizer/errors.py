from typing import Any, Dict


def make_error(reason: str) -> Dict[str, Any]:
    return {
        "success": False,
        "normalized_input": None,
        "error": f"NORMALIZATION_ERROR: {reason}",
        "debug": {},
    }
