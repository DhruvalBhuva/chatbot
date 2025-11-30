# backend/main.py

import asyncio
import threading
from typing import TypedDict, Annotated

import aiosqlite
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# from backend.llm.openai_llm import get_llm_with_tools
from backend.llm.groq_llm import get_llm_with_tools

from backend.tools.search_tool import search_tool
from backend.tools.stock_tool import get_stock_price
from backend.mcp.mcp_client import load_mcp_tools


load_dotenv()

# --- Async Setup from original backend.py ---
# Dedicated async loop for backend tasks
_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()


def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    """Run an async coroutine on the backend thread synchronously."""
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)


# -------------------
# 1. Tools Setup
# -------------------
mcp_tools = load_mcp_tools(run_async)
tools = [search_tool, get_stock_price, *mcp_tools]
llm_with_tools = get_llm_with_tools(tools)


# -------------------
# 2. State
# -------------------
class ChatState(TypedDict):
    """LangGraph state structure."""

    messages: Annotated[list[BaseMessage], add_messages]


# -------------------
# 3. Nodes
# -------------------
async def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools) if tools else None


# -------------------
# 4. Checkpointer
# -------------------
async def _init_checkpointer():
    """Initializes the SQLite checkpointer in the data directory."""
    # Ensure the 'data' directory exists for the database file
    import os

    os.makedirs("database", exist_ok=True)
    conn = await aiosqlite.connect(database="database/chatbot.db")
    return AsyncSqliteSaver(conn)


checkpointer = run_async(_init_checkpointer())

# -------------------
# 5. Graph
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")

if tool_node:
    graph.add_node("tools", tool_node)
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
else:
    graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)


# -------------------
# 6. Helper
# -------------------
async def _alist_threads():
    """Retrieves all thread IDs from the checkpointer."""
    all_threads = set()
    async for checkpoint in checkpointer.alist(None):
        # The key is thread_id in the configurable section of the config
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def retrieve_all_threads():
    """Synchronous wrapper for retrieving all thread IDs."""
    return run_async(_alist_threads())
