
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate, SystemMessagePromptTemplate, 
                                    MessagesPlaceholder)
from langgraph.graph import END, StateGraph, MessageGraph
from langgraph.prebuilt import create_react_agent
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.tools import tool
from typing import Annotated, List
import requests
import smtplib
from email.mime.text import MIMEText
from langgraph.prebuilt import ToolNode
from langchain_core.tools import StructuredTool
import os
from langchain_core.messages import BaseMessage

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

@tool
def send_email(body: Annotated[str,"Body of an alerting mail"]) -> str:
    """Send an alerting email regarding the status of Kubernetes cluster to the operation team"""

    msg = MIMEText(body)
    msg["Subject"] = "Kubernetes Cluster Alert"
    msg["From"] = os.environ.get("MAIL_FROM")
    msg["To"] = os.environ.get("MAIL_TO")
    mail_username = os.environ.get("SMTP_USERNAME")
    mail_password = os.environ.get("SMTP_PASSWORD")

    try:
        with smtplib.SMTP(os.environ.get("SMTP_SERVER"), 587) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(mail_username, mail_password)
                server.send_message(msg)
        print("Mail sent to the operation team")
        return "Mail sent to the operation team"
    except Exception as e:
     return f"Failed to send email: {str(e)}"


def alerting_agent(state: dict): 
    
    llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(""" You are a helpful assistant that email with the status of the cluster to the operation team.
                                """),
            AIMessage(content = state["messages"][-1].content)
        ]
    ) 
    
    result = prompt | llm.bind_tools(
        tools=[send_email], tool_choice="send_email")
    
    return result


tool_node = ToolNode(tools =[
        send_email
    ], )

def tool(state: dict):
        
    return tool_node.invoke({
        "messages": [
            AIMessage(content="", tool_calls=state.tool_calls)
        ]
    })


def should_continue(state:dict):
    if (hasattr(state, "tool_calls") == False or state.tool_calls == []):
        return END
    else:
        return "execute_tools"

if __name__ == "__main__":
    
    
    # react_prompt = ChatPromptTemplate.from_messages(
    #     [
    #         SystemMessagePromptTemplate.from_template_file("prompts/system_message.prompt", input_variables=[""]),
    #         HumanMessagePromptTemplate(prompt = prompt)
    #     ]
    # )   
    
   print("Starting the agent...")
    
   llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    
   react_agent = create_react_agent(
    model=llm,  
    tools=[query_prometheus],  
    prompt="""You are a helpful assistant that can answer question regarding the status of cluster.
        You can know the status of cluster through the PromQL query to the Prometheus. 
        If you dont know the answer, you can ask the user to provide more information.""",
    )
      
   wrapper = StateGraph(dict)
   wrapper.add_node("prometheus_agent", react_agent) 
   
   wrapper.add_node("alerting_agent", alerting_agent) 
   wrapper.add_node("execute_tools", tool)
   wrapper.set_entry_point("prometheus_agent")
   wrapper.add_edge("prometheus_agent", "alerting_agent") 
   wrapper.add_conditional_edges("alerting_agent", should_continue)
   wrapper.add_edge("execute_tools", END)
   
   wrapper.set_entry_point("prometheus_agent")
      
   graph = wrapper.compile() 

#    graph.get_graph().draw_mermaid_png(output_file_path="graph2.png")
#    print(graph.get_graph().draw_ascii())
   
   messages = graph.invoke(
    {"messages": [{"role": "user", "content": "How many replicas has the deployment j1p-ws-gtw-reg-be in the j1p namespace?"}]},
    )
   
   print(messages["messages"][-1].content)
   