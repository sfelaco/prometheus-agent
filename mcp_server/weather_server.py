from typing import List
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Settings
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("Weather")
mcp.settings.port = 8000

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get weather for location."""
    return "Hot as hell"

if __name__ == "__main__":
    mcp.run(transport="sse")