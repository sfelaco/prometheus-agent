
import os
import smtplib
from email.mime.text import MIMEText
from typing import Annotated

import requests
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (ChatPromptTemplate,
                                    MessagesPlaceholder)
from langchain_core.tools import tool
from langchain_openai.chat_models import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

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
        return "Email sent to the operation team"
    except Exception as e:
     return f"Failed to send email: {str(e)}"


def alerting_agent(state: AgentState): 
    
    llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(""" You are a helpul assistant that evaluate the status of Kubernetes cluster and can send alerting email to the operation team.
                              Send the alerting email only if status of the cluster has an critial issues: 
                                1. The number of replicas of a deployment is less than the desired number of replicas.
                                2. The number of pods in a node is greater than the maximum number of pods allowed.
                                3. The CPU usage of a pod is greater than the maximum CPU limit set for that pod.
                                4. The memory usage of a pod is greater than the maximum memory limit set for that pod.
                                5. The number of restarts of a pod is greater than the 1. 
                                
                                If the status of the cluster is ok, you MUST not send any email, in this case, you should return the message 
                                "The status of the cluster is ok".
                                """),
            MessagesPlaceholder(variable_name="messages"),
        ]
    ) 
    
    result = prompt | llm.bind_tools(
        tools=[send_email], tool_choice="auto")
    
    return {"messages": result.invoke({"messages": [state["messages"][-1]]}) }


tool_node = ToolNode(tools =[
        send_email
    ], )

# def tool(state: AgentState):
        
#     return tool_node.invoke({
#         "messages": [
#             AIMessage(content="", tool_calls=state["messages"][-1].tool_calls)
#         ]
#     })



if __name__ == "__main__":

   print("Starting the agent...")
    
   llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    
   react_agent = create_react_agent(
    model=llm,  
    tools=[query_prometheus],  
    prompt="""You are a helpful assistant that can answer question regarding the status of cluster.
        You can know the status of cluster through the PromQL query to the Prometheus. 
        If you dont know the answer, you can ask the user to provide more information.""",
    )
      
   wrapper = StateGraph(AgentState)
   wrapper.add_node("prometheus_agent", react_agent) 
   
   wrapper.add_node("alerting_agent", alerting_agent) 
   wrapper.add_node("execute_tools", tool_node)
   wrapper.set_entry_point("prometheus_agent")
   wrapper.add_edge("prometheus_agent", "alerting_agent") 
   wrapper.add_edge("alerting_agent", "execute_tools")
   wrapper.add_edge("execute_tools", END)
   
   wrapper.set_entry_point("prometheus_agent")
      
   graph = wrapper.compile() 

   graph.get_graph().draw_mermaid_png(output_file_path="graph2.png")
   
   messages = graph.invoke(
    {"messages": [{"role": "user", "content": "How many desidered and running replicas has the deployment j1p-ws-gtw-reg-be in the j1p namespace?"}]},
    )
   
   print("Cluster status:")
   print(messages["messages"][-2].content)
   print(" \nAgent evaluation:")
   print(messages["messages"][-1].content)
   