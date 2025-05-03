
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage
from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate, SystemMessagePromptTemplate,
                                    MessagesPlaceholder)
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.tools import tool
from typing import Annotated, List
import requests


load_dotenv()

@tool
def query_prometheus(query: Annotated[str,"Prometheus query in PromQL syntax"]) -> str: 
    """Execute a PromQL query to the Prometheus"""
    
    prometheus_endpoint = "http://localhost:9090/api/v1/query"
    params = {"query": query}
    response = requests.get(prometheus_endpoint, params=params)
    response.raise_for_status()
    data = response.json()
    return str(data)


if __name__ == "__main__":
    
    
    # react_prompt = ChatPromptTemplate.from_messages(
    #     [
    #         SystemMessagePromptTemplate.from_template_file("prompts/system_message.prompt", input_variables=[""]),
    #         HumanMessagePromptTemplate(prompt = prompt)
    #     ]
    # )   
    
   print("Starting the agent...")
    
   llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    
   agent = create_react_agent(
    model=llm,  
    tools=[query_prometheus],  
    prompt="""You are a helpful assistant that can answer question regarding the status of cluster.
        You can know the status of cluster through the PromQL query to the Prometheus. 
        If you dont know the answer, you can ask the user to provide more information.""",
    compile = False
    )
   
   agent.get_graph().draw_mermaid_png(output_file_path="graph.png")
   
   messages = agent.invoke(
    {"messages": [{"role": "user", "content": "How many replicas has the deployment j1p-ws-gtw-reg-be in the j1p namespace?"}]},
    )
   
   print(messages["messages"][-1].content)
   