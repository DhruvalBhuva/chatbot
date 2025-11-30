# backend/mcp/mcp_client.py

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "arith": {
            "transport": "stdio",
            "command": "python3",
            "args": ["/Users/dhruval/Desktop/mcp-math-server/main.py"],
        },
        "expense": {
            "transport": "streamable_http",  # if this fails, try "sse"
            "url": "https://splendid-gold-dingo.fastmcp.app/mcp",
        },
    }
)


def load_mcp_tools(run_async_func) -> list[BaseTool]:
    """
    Loads tools from the MultiServerMCPClient using a synchronous wrapper
    for an async call.

    Args:
        run_async_func: A function to run an async coroutine synchronously.

    Returns:
        A list of BaseTool objects from the MCP client.
    """
    try:
        # Assumes run_async_func is the synchronous wrapper for client.get_tools()
        return run_async_func(client.get_tools())
    except Exception:
        # Handle cases where the MCP servers are not running/reachable
        return []
