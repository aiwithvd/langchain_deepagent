from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from app.core.config import get_settings

settings = get_settings()

_THINK_PROMPT = """\
You are a precise reasoning engine. Reason through the following question \
step-by-step before committing to an answer.

Question / Problem:
{thought}

Respond in exactly this format:

[Question]
<restate the question in your own words>

[Reasoning]
Step 1: <first logical step>
Step 2: <next step>
... (as many steps as needed)

[Conclusion]
<your clear, direct conclusion or recommended next action>
"""


@tool
async def think(thought: str) -> str:
    """
    Reason step-by-step about a question or problem before acting.

    Use this skill BEFORE making decisions that involve trade-offs,
    ambiguity, or multiple possible approaches. Returns structured
    chain-of-thought reasoning with a clear conclusion.

    Args:
        thought: The question, problem, or situation to reason about.

    Returns:
        Structured reasoning with [Question], [Reasoning], and [Conclusion] sections.
    """
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,  # slight creativity for reasoning
    )
    prompt = _THINK_PROMPT.format(thought=thought)
    response = await llm.ainvoke(prompt)
    return str(response.content)
