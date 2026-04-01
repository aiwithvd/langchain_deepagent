from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from app.core.config import get_settings

settings = get_settings()

_PLAN_PROMPT = """\
You are a meticulous project planner. Decompose the following goal into a \
clear, ordered, actionable plan.

Goal:
{goal}

{context_section}

Respond in exactly this format:

## Plan: <short goal title>

**Goal:** <one-sentence description of what success looks like>

### Steps
1. [ ] <specific atomic action> — tool: <which skill to use: think/web_search/write_report/none>
2. [ ] <specific atomic action> — tool: <skill>
... (continue until the goal is fully covered)

**Success criteria:** <how we will know the goal has been achieved>

Keep each step atomic (one action). Order steps by dependency.
"""


@tool
async def plan(goal: str, context: str = "") -> str:
    """
    Decompose a complex goal into ordered, actionable sub-tasks.

    Use this skill at the START of any multi-step task to create a
    structured execution plan before taking action. Each step specifies
    what to do and which other skill to use.

    Args:
        goal:    The high-level objective to achieve.
        context: Optional background information relevant to the goal.

    Returns:
        A numbered markdown plan with steps, assigned tools, and success criteria.
    """
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
    )
    context_section = f"Context:\n{context}" if context else ""
    prompt = _PLAN_PROMPT.format(goal=goal, context_section=context_section)
    response = await llm.ainvoke(prompt)
    return str(response.content)
