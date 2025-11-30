# backend/llm/openai_llm.py

from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool


def get_llm_with_tools(tools: list[BaseTool]):
    """
    Initializes the ChatOpenAI LLM and binds the provided tools.

    Args:
        tools: A list of BaseTool objects.

    Returns:
        The ChatOpenAI instance, optionally bound with tools.
    """
    llm = ChatOpenAI(temperature=0)  # Using a low temperature for tool use
    return llm.bind_tools(tools) if tools else llm
