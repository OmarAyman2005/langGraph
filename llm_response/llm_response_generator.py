from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from llm_response.llm_response_prompt import SYSTEM_PROMPT
from llm_response.llm_utils import generation_llm


def make_generation_success(raw_llm_output: str) -> Dict[str, Any]:
    return {
        "generation_success": True,
        "generation_error": None,
        "raw_llm_output": raw_llm_output,
    }


def make_generation_failure(error: str) -> Dict[str, Any]:
    return {
        "generation_success": False,
        "generation_error": error,
        "raw_llm_output": None,
    }


def build_llm_human_prompt(normalized_input: str) -> str:
    return f"""Normalized problem:
{normalized_input}
"""


def generate_llm_response(normalized_input: str) -> Dict[str, Any]:
    """
    Main LLM Response Generator component.

    Input:
    - normalized_input:
      The final normalized prompt produced by the Normalizer.

    Output success:
    {
        "generation_success": true,
        "generation_error": null,
        "raw_llm_output": "Answer: ...\\nSteps:\\n..."
    }

    Output failure:
    {
        "generation_success": false,
        "generation_error": "...",
        "raw_llm_output": null
    }

    Notes:
    - This component does not parse or validate the LLM output.
    - Parser 2 is responsible for validating the response schema.
    - The Verifier is responsible for judging logical validity.
    """

    if not isinstance(normalized_input, str):
        return make_generation_failure("Normalized input must be a string.")

    if not normalized_input.strip():
        return make_generation_failure("Empty normalized input.")

    try:
        response = generation_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_llm_human_prompt(normalized_input)),
            ]
        )

        raw_llm_output = response.content.strip()

        if not raw_llm_output:
            return make_generation_failure("LLM returned an empty response.")

        return make_generation_success(raw_llm_output)

    except Exception as exc:
        return make_generation_failure(f"LLM response generation failed: {exc}")


def generate_raw_llm_response(normalized_input: str) -> str:
    """
    Convenience helper for tests/manual scripts that only need the raw text.

    Raises RuntimeError if generation fails.
    """

    result = generate_llm_response(normalized_input)

    if result["generation_success"] is False:
        raise RuntimeError(result["generation_error"])

    return result["raw_llm_output"]