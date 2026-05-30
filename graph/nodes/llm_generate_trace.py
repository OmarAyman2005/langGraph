from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import GraphState
from config import STATUS_GENERATED
from llm_response.llm_utils import generation_llm
from prompts.llm_response_prompt import SYSTEM_PROMPT


def llm_generate_trace_node(state: GraphState) -> GraphState:
    """
    LLM Response Generator node.

    Input:
    - normalized_input

    Task:
    - Send the normalized prompt directly to the generation LLM.
    - Force the LLM to produce a strict reasoning trace.

    Output:
    - raw_llm_output
    - status = generated
    """

    normalized_input = state.get("normalized_input", "").strip()

    human_prompt = f"""Normalized problem:
{normalized_input}
"""

    response = generation_llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]
    )

    return {
        **state,
        "raw_llm_output": response.content.strip(),
        "status": STATUS_GENERATED,
    }