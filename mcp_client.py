import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

async def main():
    
    async with MultiServerMCPClient(
    {
        # "math": {
        #     "command": "python",
        #     # Make sure to update to the full absolute path to your math_server.py file
        #     "args": ["./mcp_server/math_server.py"],
        #     "transport": "stdio",
        # },
        # "weather": {
        #     # make sure you start your weather server on port 8000
        #     "url": "http://localhost:8000/sse",
        #     "transport": "sse",
        # },
        "prometheus": {
            # make sure you start your weather server on port 8000
            "url": "http://localhost:8000/sse",
            "transport": "sse",
        },      
        
    }
) as client:
        print("Starting the client...")
        agent = create_react_agent("openai:gpt-4.1", client.get_tools())
        #math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
        #weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        prometheus_response = await agent.ainvoke({"messages": "How many desidered and running replicas has the deployment j1p-ws-gtw-reg-be in the j1p namespace?"})
        print(prometheus_response['messages'][-1].content)



if __name__ == "__main__":
    asyncio.run(main())