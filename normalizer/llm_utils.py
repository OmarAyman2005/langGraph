import json
from typing import Any, Dict


def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"LLM did not return valid JSON: {text}")

    return json.loads(cleaned[start : end + 1])


def call_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    try:
        # local import to avoid hard dependency at module import time
        from langchain_core.messages import (
            SystemMessage as _SystemMessage,
            HumanMessage as _HumanMessage,
        )
        from langchain_ollama import ChatOllama as _ChatOllama

        llm = _ChatOllama(model="llama3.1:8b", temperature=0)

        response = llm.invoke(
            [
                _SystemMessage(content=system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )

        return extract_json(response.content)
    except Exception as e:
        # Bubble up a clear exception so callers can decide fallback behavior.
        raise RuntimeError(f"LLM call failed: {e}")
