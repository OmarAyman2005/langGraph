from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from graph.state import GraphState
from config import STATUS_GENERATED
from prompts import SYSTEM_PROMPT


def llm_generate_trace_node(state: GraphState) -> GraphState:
    llm = ChatOllama(model="llama3.1:8b")

    parsed_problem = state.get("parsed_problem", {})
    premises_dict = parsed_problem.get("premises", {})
    question = parsed_problem.get("question", "")

    premises = list(premises_dict.values())

    premises_text = "\n".join(
        [f"P{i+1}: {premise}" for i, premise in enumerate(premises)]
    )

    human_prompt = f"""Premises:
{premises_text}

Conclusion:
{question}
"""

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ]
    )

    return {
        **state,
        "premises": premises,
        "question": question,
        "raw_llm_output": response.content,
        "status": STATUS_GENERATED,
    }
