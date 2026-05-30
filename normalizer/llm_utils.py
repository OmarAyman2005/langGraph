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

    return json.loads(cleaned[start:end + 1])


def call_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_ollama import ChatOllama

        from config import NORMALIZER_LLM_MODEL, NORMALIZER_TEMPERATURE

        llm = ChatOllama(
            model=NORMALIZER_LLM_MODEL,
            temperature=NORMALIZER_TEMPERATURE,
        )

        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        return extract_json(response.content)

    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")