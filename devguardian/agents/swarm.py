# 🛡️ DevGuardian Project — Core Module
"""
🤖 DevGuardian Agent Swarm
===========================
A 3-agent LangGraph pipeline that tackles tasks as a team:
  1. 🖊️  Coder   — Writes or fixes the code
  2. 🧪  Tester  — Identifies test scenarios and potential breakage
  3. 🔍  Reviewer — Enforces project conventions and security

The final output is the Reviewer's verdict and the Coder's finished code.
"""

import os
from typing import TypedDict, Annotated, List
from typing_extensions import Required

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

from devguardian.utils.file_reader import build_project_context


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class SwarmState(TypedDict):
    task:           Required[str]
    project_path:   Required[str]
    project_dna:    str           # enriched context (loaded once)
    code_draft:     str           # Coder's output
    test_report:    str           # Tester's output
    final_verdict:  str           # Reviewer's output
    messages:       Annotated[List[BaseMessage], "trace"]


# ---------------------------------------------------------------------------
# Shared LLM factory (lazy — created once per swarm run)
# ---------------------------------------------------------------------------
def _get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=temperature,
    )


# ----------------------------------------------------------------及ひ-------------------------------------
# Node: Load Project DNA (runs once at start)
# ---------------------------------------------------------------------------
def load_dna(state: SwarmState) -> SwarmState:
    dna = build_project_context(state["project_path"])
    return {**state, "project_dna": dna, "messages": state.get("messages", [])}


# ---------------------------------------------------------------------------
# Node: Coder Agent
# ---------------------------------------------------------------------------
def coder_agent(state: SwarmState) -> SwarmState:
    llm = _get_llm(temperature=0.3)

    system = SystemMessage(content=(
        "You are an expert Python Coder Agent in the DevGuardian Swarm. "
        "Your sole job is to write or fix code. "
        "Given a task and the project context, produce complete, correct Python code. "
        "Return ONLY code. No explanations, no markdown fences."
    ))
    user = HumanMessage(content=(
        f"## Project DNA\n{state['project_dna'][:3000]}\n\n"
        f"## Task\n{state['task']}\n\n"
        "Write the implementation now."
    ))

    response: AIMessage = llm.invoke([system, user])
    code = response.content.strip()

    # Strip markdown fences if model adds them
    if "```" in code:
        lines = [l for l in code.splitlines() if not l.strip().startswith("```")]
        code = "\n".join(lines).strip()

    return {
        **state,
        "code_draft": code,
        "messages": state.get("messages", []) + [
            HumanMessage(content="[Coder produced draft code]")
        ],
    }


# ---------------------------------------------------------------------------
# Node: Tester Agent
# ---------------------------------------------------------------------------
def tester_agent(state: SwarmState) -> SwarmState:
    llm = _get_llm(temperature=0.4)

    system = SystemMessage(content=(
        "You are a meticulous Tester Agent in the DevGuardian Swarm. "
        "You audit code written by the Coder for bugs, edge cases, and missing validation. "
        "Report your findings clearly with bullet points. "
        "Do NOT rewrite the code — only surface issues and test scenarios."
    ))
    user = HumanMessage(content=(
        f"## Coder's Draft\n```python\n{state['code_draft']}\n```\n\n"
        f"## Original Task\n{state['task']}\n\n"
        "List all bugs, missing edge cases, and test scenarios you would write. "
        "Be specific — cite exact function names or line contexts."
    ))

    response: AIMessage = llm.invoke([system, user])
    return {
        **state,
        "test_report": response.content.strip(),
        "messages": state.get("messages", []) + [
            HumanMessage(content="[Tester produced report]")
        ],
    }


# ---------------------------------------------------------------------------
# Node: Reviewer Agent (also incorporates Tester feedback into final code)
# ---------------------------------------------------------------------------
def reviewer_agent(state: SwarmState) -> SwarmState:
    llm = _get_llm(temperature=0.2)

    system = SystemMessage(content=(
        "You are a senior Code Reviewer Agent in the DevGuardian Swarm. "
        "You receive the Coder's draft and the Tester's report. "
        "Your job: produce the FINAL, production-ready version of the code, "
        "incorporating all Tester feedback and ensuring it matches project conventions. "
        "Format your response as:\n"
        "## Verdict\n<your assessment>\n\n## Final Code\n<complete code>\n\n## Changes Made\n<bullet list>"
    ))
    user = HumanMessage(content=(
        f"## Project DNA\n{state['project_dna'][:2000]}\n\n"
        f"## Task\n{state['task']}\n\n"
        f"## Coder's Draft\n```python\n{state['code_draft']}\n```\n\n"
        f"## Tester's Report\n{state['test_report']}\n\n"
        "Produce the final verdict and production-ready code."
    ))

    response: AIMessage = llm.invoke([system, user])
    return {
        **state,
        "final_verdict": response.content.strip(),
        "messages": state.get("messages", []) + [
            HumanMessage(content="[Reviewer produced final verdict]")
        ],
    }


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def create_swarm_graph():
    workflow = StateGraph(SwarmState)

    workflow.add_node("load_dna", load_dna)
    workflow.add_node("coder", coder_agent)
    workflow.add_node("tester", tester_agent)
    workflow.add_node("reviewer", reviewer_agent)

    workflow.set_entry_point("load_dna")
    workflow.add_edge("load_dna", "coder")
    workflow.add_edge("coder", "tester")
    workflow.add_edge("tester", "reviewer")
    workflow.add_edge("reviewer", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def run_swarm(task: str, project_path: str) -> str:
    """
    Run the 3-agent swarm on a task.

    Args:
        task:         What to build or fix.
        project_path: Absolute path to the project root for context.

    Returns:
        The Reviewer's final verdict + production-ready code.
    """
    graph = create_swarm_graph()

    initial_state: SwarmState = {
        "task": task,
        "project_path": project_path,
        "project_dna": "",
        "code_draft": "",
        "test_report": "",
        "final_verdict": "",
        "messages": [],
    }

    result = await graph.ainvoke(initial_state)
    final = result["final_verdict"]
    test_notes = result["test_report"]

    return (
        f"# 🤖 DevGuardian Agent Swarm Report\n\n"
        f"**Task:** {task}\n\n"
        f"---\n\n"
        f"## 🧪 Tester's Notes\n{test_notes}\n\n"
        f"---\n\n"
        f"{final}"
    )
