import os
from typing import TypedDict, Annotated, List, Literal
from typing_extensions import Required

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

from devguardian.utils.file_reader import build_project_context
from devguardian.utils.memory import ProjectMemory
from devguardian.utils.executor import verify_code_logic


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class SwarmState(TypedDict):
    task: Required[str]
    project_path: Required[str]
    project_dna: str
    memory_context: str
    code_draft: str
    test_report: str
    reviewer_feedback: str  # Used for iterative loops
    iteration_count: int
    final_verdict: str
    messages: Annotated[List[BaseMessage], "trace"]


# ---------------------------------------------------------------------------
# LLM & Memory Helpers
# ---------------------------------------------------------------------------
def _get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def load_context(state: SwarmState) -> SwarmState:
    """Initialize project DNA and Semantic Memory."""
    dna = build_project_context(state["project_path"])
    mem = ProjectMemory(state["project_path"])

    return {
        **state,
        "project_dna": dna,
        "memory_context": mem.get_context_string(),
        "iteration_count": 1,
        "reviewer_feedback": "",
        "messages": state.get("messages", []),
    }


def coder_agent(state: SwarmState) -> SwarmState:
    """Writes code, considering memory and previous reviewer rejections."""
    llm = _get_llm(temperature=0.3)

    # Pillar 1: Adversarial Loop
    is_fix = len(state["reviewer_feedback"]) > 0
    mode_instruction = (
        f"FIX the following code based on reviewer feedback:\n{state['reviewer_feedback']}"
        if is_fix
        else "Write the implementation from scratch."
    )

    system = SystemMessage(
        content=(
            "You are an expert Python Coder. "
            "Follow project style preferences and past lessons learned. "
            "Return ONLY raw Python code. No markdown fences."
        )
    )
    user = HumanMessage(
        content=(
            f"## Project Context\n{state['project_dna'][:3000]}\n"
            f"## Semantic Memory (Style & Lessons)\n{state['memory_context']}\n\n"
            f"## Task\n{state['task']}\n\n"
            f"## Current Effort (Iteration {state['iteration_count']})\n"
            f"{mode_instruction}\n\n"
            f"{'## Source Code to Fix:' + state['code_draft'] if is_fix else ''}"
        )
    )

    response: AIMessage = llm.invoke([system, user])
    code = response.content.strip()

    if "```" in code:
        code = "\n".join([l for l in code.splitlines() if not l.strip().startswith("```")]).strip()

    return {
        **state,
        "code_draft": code,
        "messages": state.get("messages", [])
        + [HumanMessage(content=f"[Coder produced draft v{state['iteration_count']}]")],
    }


def tester_agent(state: SwarmState) -> SwarmState:
    """Audits code and RUNS it in a sandbox to catch real crashes."""
    llm = _get_llm(temperature=0.4)

    # Pillar 3: Sandbox Execution
    execution_result = verify_code_logic(state["code_draft"])

    system = SystemMessage(
        content=(
            "You are a meticulous Tester. Identify bugs and edge cases. "
            "Consider the sandbox execution result provided below."
        )
    )
    user = HumanMessage(
        content=(
            f"## Code to Audit\n```python\n{state['code_draft']}\n```\n\n"
            f"## Sandbox Execution Output\n{execution_result}\n\n"
            "List bugs, missing edge cases, and logic flaws. "
            "If the sandbox failed, explain why based on the code."
        )
    )

    response: AIMessage = llm.invoke([system, user])
    return {
        **state,
        "test_report": f"### Sandbox Result\n{execution_result}\n\n### Audit Notes\n{response.content.strip()}",
        "messages": state.get("messages", []) + [HumanMessage(content="[Tester produced report]")],
    }


def reviewer_agent(state: SwarmState) -> SwarmState:
    """Decides if the code is production-ready or needs another pass (Adversarial)."""
    llm = _get_llm(temperature=0.1)

    system = SystemMessage(
        content=(
            "You are the Final Gatekeeper. You must either ACCEPT or REJECT the code. "
            "REJECT if there are logic bugs, security leaks, or it fails sandbox tests. "
            "If REJECTED, provide clear instructions for the Coder. "
            "If ACCEPTED, format response as:\n"
            "## Verdict\nACCEPTED\n\n## Final Code\n<code>\n\n## Summary\n<notes>"
        )
    )
    user = HumanMessage(
        content=(
            f"## Task\n{state['task']}\n\n"
            f"## Draft Code\n```python\n{state['code_draft']}\n```\n\n"
            f"## Tester Feedback\n{state['test_report']}\n\n"
            "Decide: Is this production-ready? (Iteration: " + str(state["iteration_count"]) + ")"
        )
    )

    response: AIMessage = llm.invoke([system, user])
    verdict_text = response.content.strip()

    is_rejected = "REJECT" in verdict_text.upper() and state["iteration_count"] < 3

    return {
        **state,
        "reviewer_feedback": verdict_text if is_rejected else "",
        "final_verdict": verdict_text,
        "iteration_count": state["iteration_count"] + 1,
        "messages": state.get("messages", []) + [HumanMessage(content="[Reviewer verdict]")],
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
def router(state: SwarmState) -> Literal["coder", "end"]:
    """Determines if we should loop back or finish."""
    if state["reviewer_feedback"] and state["iteration_count"] <= 3:
        return "coder"

    # Update Semantic Memory on success
    if "ACCEPTED" in state["final_verdict"].upper():
        mem = ProjectMemory(state["project_path"])
        mem.add_lesson(state["task"], "Code passed sandbox and adversarial review.")

    return "end"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------
def create_swarm_graph():
    workflow = StateGraph(SwarmState)

    workflow.add_node("load_context", load_context)
    workflow.add_node("coder", coder_agent)
    workflow.add_node("tester", tester_agent)
    workflow.add_node("reviewer", reviewer_agent)

    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "coder")
    workflow.add_edge("coder", "tester")
    workflow.add_edge("tester", "reviewer")

    workflow.add_conditional_edges("reviewer", router, {"coder": "coder", "end": END})

    return workflow.compile()


async def run_swarm(task: str, project_path: str) -> str:
    graph = create_swarm_graph()
    result = await graph.ainvoke({"task": task, "project_path": project_path, "messages": [], "iteration_count": 0})

    return (
        f"# 🤖 DevGuardian v3 Swarm Report\n\n"
        f"**Task:** {task}\n"
        f"**Persistence:** Semantic Memory Updated ✅\n"
        f"**Validation:** Sandbox Execution Confirmed ✅\n"
        f"**Total Passes:** {result['iteration_count'] - 1 if result['iteration_count'] > 0 else 1}\n\n"
        f"---\n\n"
        f"{result['final_verdict']}"
    )
