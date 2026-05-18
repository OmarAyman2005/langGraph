from langchain_ollama import ChatOllama as _ChatOllama

from config import GENERATION_LLM_MODEL, GENERATION_TEMPERATURE


generation_llm = _ChatOllama(
    model=GENERATION_LLM_MODEL,
    temperature=GENERATION_TEMPERATURE,
)