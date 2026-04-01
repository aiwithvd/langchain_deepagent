"""
Agent factory — creates and caches the DeepAgent singleton.

Uses async_create_deep_agent() from the deepagents package, which returns
a compiled LangGraph graph with built-in MemorySaver for multi-turn sessions.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from deepagents import async_create_deep_agent
from langchain_ollama import ChatOllama

from app.agent.tools import ALL_TOOLS
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

settings = get_settings()
log = get_logger(__name__)

_agent: CompiledGraph | None = None
_lock = asyncio.Lock()

_SYSTEM_INSTRUCTIONS = """\
You are a deep research assistant powered by LangChain DeepAgent.

You have four specialised skills at your disposal:

1. **think** — use this to reason step-by-step before making decisions
2. **plan**  — use this to decompose complex goals into ordered steps
3. **web_search** — use this to retrieve current, factual information from the web
4. **write_report** — use this to format your findings into a professional report

## Working Style
- For simple questions: answer directly.
- For complex tasks: always PLAN first, then execute the plan step-by-step.
- Before any significant decision: THINK through the options.
- When the user asks for a report or research: SEARCH, THINK, then WRITE_REPORT.
- Always cite your sources when you have searched the web.

## Output Quality
- Be concise but complete.
- Use markdown formatting in your answers.
- If a plan changes, say so explicitly.
- Never fabricate facts — if uncertain, search for the information.
"""


async def get_agent() -> CompiledGraph:
    """
    Returns the compiled DeepAgent (singleton, thread-safe).

    On first call, creates the agent and warms it up.
    Subsequent calls return the cached instance immediately.
    """
    global _agent

    if _agent is not None:
        return _agent

    async with _lock:
        # Double-checked locking: another coroutine may have initialised it
        if _agent is not None:
            return _agent

        log.info(
            "Initialising DeepAgent",
            model=settings.ollama_model,
            ollama_url=settings.ollama_base_url,
            skills_dir=settings.skills_dir,
        )

        model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        )

        _agent = await async_create_deep_agent(
            model=model,
            tools=ALL_TOOLS,
            instructions=_SYSTEM_INSTRUCTIONS,
            skills=[settings.skills_dir],
        )

        log.info("DeepAgent ready")

    return _agent
