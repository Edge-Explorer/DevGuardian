# 🛡️ DevGuardian Project — Core Module
"""
🛠️ DevGuardian Engineering Agent (Stateful)
Powered by LangGraph, LangChain, and SQLite.
"""

import os
from typing import Annotated, TypedDict, List, Union
from typing_extensions import Required

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from devguardian.tools.git_ops import git_status, git_diff, git_add, git_commit
from devguardian.tools.debugger import debug_error

# ---------------------------------------------------------------------------
# 1. State Definition
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    """The graph state - passed between nodes."""
    messages: Annotated[List[BaseMessage], "The conversation history"]
    project_path: Required[str]
    task_description: str
    is_resolved: bool

# ---------------------------------------------------------------------------
# 2. Tool Wrappers (for LangChain compatibility)
# ---------------------------------------------------------------------------
# We wrap our existing tools to make them easily callable by LangChain
@tool
def check_repo_status(repo_path: str):
    """Check the current git status of the repository."""
    return git_status(repo_path)

@tool
def analyze_error(error_text: str, code_context: str = ""):
    """Analyze a bug/error and suggest a fix using Gemini reasoning."""
    return debug_error(error_message=error_text, code_snippet=code_context)

# ---------------------------------------------------------------------------
# 3. Graph Logic
# ---------------------------------------------------------------------------

def create_engineer_graph():
    # Initialize the LLM (Gemini 2.0 Flash)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2
    )
    
    # Define our tools
    tools = [check_repo_status, analyze_error]
    llm_with_tools = llm.bind_tools(tools)
    
    # -- Node: Planner --
    def call_model(state: AgentState):
        system_msg = SystemMessage(content=(
            "You are the DevGuardian Engineering Agent. "
            "Your goal is to solve coding tasks autonomously. "
            "1. Analyze the current state of the repo.\n"
            "2. Decide which tool to call.\n"
            "3. After tool results come back, verify if the task is complete.\n"
            "Work in the repo path: " + state['project_path']
        ))
        response = llm_with_tools.invoke([system_msg] + state['messages'])
        return {"messages": [response]}

    # -- Building the Graph --
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    
    # Define Edges
    workflow.set_entry_point("agent")
    
    # Conditional logic: Should we keep going or stop?
    def should_continue(state: AgentState):
        last_message = state['messages'][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()