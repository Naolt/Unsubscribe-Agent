from fastmcp import FastMCP
import asyncio
from typing import Optional

from main import unsubscribe_by_request


mcp = FastMCP("Unsubscribe Agent MCP")


@mcp.tool
async def unsubscribe(query: str) -> str:
    """Attempt to unsubscribe from a sender or service based on the natural-language query.

    Example: "Unsubscribe from Atlassian marketing emails".
    Returns a short status string.
    """
    try:
        message = await unsubscribe_by_request(query)
        return message
    except Exception as exc:
        return f"Error during unsubscribe flow: {exc}"


@mcp.tool
def ping() -> str:
    """Health-check tool to verify the MCP server is responsive."""
    return "pong"


if __name__ == "__main__":
    mcp.run()