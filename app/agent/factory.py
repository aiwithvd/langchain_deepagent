"""
Agent factory — creates and caches the DeepAgent singleton.

Uses create_deep_agent() from the deepagents package, which returns
a compiled LangGraph graph. FilesystemBackend enables SKILL.md discovery
from disk. checkpointer=True wires in MemorySaver for multi-turn sessions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_ollama import ChatOllama

from app.agent.tools import ALL_TOOLS
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

settings = get_settings()
log = get_logger(__name__)

_agent: CompiledStateGraph | None = None
_lock = asyncio.Lock()

# Project root = directory that contains app/ and deepagents_skills/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

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


async def get_agent() -> CompiledStateGraph:
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

        # FilesystemBackend loads SKILL.md files relative to project root
        backend = FilesystemBackend(root_dir=_PROJECT_ROOT)

        # create_deep_agent is synchronous — run in thread to avoid blocking the loop
        _agent = await asyncio.to_thread(
            create_deep_agent,
            model,
            tools=ALL_TOOLS,
            system_prompt=_SYSTEM_INSTRUCTIONS,
            skills=[settings.skills_dir],  # e.g. "deepagents_skills/skills"
            backend=backend,
            checkpointer=True,  # MemorySaver for multi-turn session memory
        )

        log.info("DeepAgent ready")

    return _agent
