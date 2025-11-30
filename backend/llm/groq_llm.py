# backend/llm/groq_llm.py

import os
from langchain_groq import ChatGroq
from langchain_core.tools import BaseTool
from dotenv import load_dotenv

load_dotenv()


def get_llm_with_tools(tools: list[BaseTool]):
    """
    Initializes the ChatGroq LLM and binds the provided tools.

    Args:
        tools: A list of BaseTool objects.

    Returns:
        The ChatGroq instance, optionally bound with tools.
    """
    # Uses GROQ_API_KEY environment variable loaded by dotenv
    llm = ChatGroq(
        temperature=0, model_name="openai/gpt-oss-120b"  # A fast, capable Groq model
    )

    # LangGraph requires the tools to be bound to the LLM
    return llm.bind_tools(tools) if tools else llm
