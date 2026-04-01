"""
Agent endpoints:

  POST /api/v1/agent/run     — blocking JSON response
  GET  /api/v1/agent/stream  — SSE streaming response

Both endpoints are rate-limited via Redis (fastapi-limiter).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sse_starlette.sse import EventSourceResponse

from app.agent.factory import get_agent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limit import get_rate_limiter
from app.models.schemas import AgentRequest, AgentResponse, ToolCallLog

router = APIRouter()
settings = get_settings()
log = get_logger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────


def _extract_response(result: dict, session_id: str, query: str, elapsed: float) -> AgentResponse:
    """Parse the LangGraph result dict into an AgentResponse."""
    messages = result.get("messages", [])

    # Final answer = last AIMessage that has no tool_calls
    answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            answer = str(msg.content)
            break

    # Build tool call log from paired AIMessage (tool_calls) + ToolMessage (output)
    tool_calls: list[ToolCallLog] = []
    pending: dict[str, str] = {}  # tool_call_id → tool_name + input

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                pending[tc["id"]] = json.dumps(
                    {"tool": tc["name"], "input": tc["args"]}, ensure_ascii=False
                )
        elif isinstance(msg, ToolMessage):
            raw = pending.pop(msg.tool_call_id, None)
            if raw:
                meta = json.loads(raw)
                tool_calls.append(
                    ToolCallLog(
                        tool=meta["tool"],
                        input=json.dumps(meta["input"], ensure_ascii=False),
                        output=str(msg.content)[:2000],  # truncate very long outputs
                    )
                )

    iterations = sum(1 for m in messages if isinstance(m, AIMessage))

    return AgentResponse(
        session_id=session_id,
        query=query,
        answer=answer,
        tool_calls=tool_calls,
        iterations=iterations,
        elapsed_seconds=round(elapsed, 3),
    )


# ── endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/agent/run",
    response_model=AgentResponse,
    summary="Run agent (blocking)",
    dependencies=[Depends(get_rate_limiter())],
)
async def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Invoke the DeepAgent and wait for the full response.

    - Pass `session_id` to continue an existing conversation thread.
    - Omit `session_id` (or pass `null`) to start a new session.
    - The returned `session_id` can be passed in subsequent requests.

    Rate limited to **{RATE_LIMIT_REQUESTS} requests / {RATE_LIMIT_SECONDS}s** per IP.
    Returns HTTP 429 when the limit is exceeded.
    """
    session_id = request.session_id or str(uuid.uuid4())
    agent = await get_agent()

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": settings.agent_recursion_limit,
    }

    log.info("agent.run.start", session_id=session_id, query_len=len(request.query))
    start = time.perf_counter()

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.query)]},
            config=config,
        )
    except Exception as exc:
        log.exception("agent.run.failed", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {exc}",
        ) from exc

    elapsed = time.perf_counter() - start
    log.info("agent.run.complete", session_id=session_id, elapsed=round(elapsed, 3))

    return _extract_response(result, session_id, request.query, elapsed)


@router.get(
    "/agent/stream",
    summary="Run agent (SSE streaming)",
    dependencies=[Depends(get_rate_limiter())],
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {}},
        }
    },
)
async def stream_agent(
    query: str,
    session_id: str | None = None,
) -> EventSourceResponse:
    """
    Invoke the DeepAgent and stream events via Server-Sent Events (SSE).

    **Event types:**

    | event        | data                              |
    |--------------|-----------------------------------|
    | `token`      | A streamed LLM token              |
    | `tool_start` | Name of the tool being called     |
    | `tool_end`   | Output returned by the tool       |
    | `done`       | Final complete answer             |
    | `error`      | Error message                     |

    Rate limited to **{RATE_LIMIT_REQUESTS} requests / {RATE_LIMIT_SECONDS}s** per IP.
    """
    session_id = session_id or str(uuid.uuid4())
    agent = await get_agent()

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": settings.agent_recursion_limit,
    }

    async def event_generator() -> AsyncIterator[dict]:
        log.info("agent.stream.start", session_id=session_id)
        final_answer_parts: list[str] = []

        try:
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=query)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and chunk.content:
                        token = str(chunk.content)
                        final_answer_parts.append(token)
                        yield {"event": "token", "data": token}

                elif kind == "on_tool_start":
                    yield {"event": "tool_start", "data": event.get("name", "")}

                elif kind == "on_tool_end":
                    output = event["data"].get("output", "")
                    yield {"event": "tool_end", "data": str(output)[:500]}

            # Signal completion with session_id so clients can continue the thread
            yield {
                "event": "done",
                "data": json.dumps({"session_id": session_id}),
            }

        except Exception as exc:
            log.exception("agent.stream.failed", session_id=session_id)
            yield {"event": "error", "data": str(exc)}

        log.info("agent.stream.complete", session_id=session_id)

    return EventSourceResponse(event_generator())
