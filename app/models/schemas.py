from typing import Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Payload for POST /api/v1/agent/run."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The question or task for the agent to handle.",
        examples=["Research the latest AI agent frameworks and write a summary report."],
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Optional session identifier to continue an existing conversation thread. "
            "Omit or pass null to start a new session."
        ),
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ToolCallLog(BaseModel):
    """Records a single tool invocation made during an agent run."""

    tool: str = Field(..., description="Name of the skill/tool that was called.")
    input: str = Field(..., description="Serialised input passed to the tool.")
    output: str = Field(..., description="Serialised output returned by the tool.")


class AgentResponse(BaseModel):
    """Response for POST /api/v1/agent/run."""

    session_id: str = Field(..., description="Session ID — reuse to continue this conversation.")
    query: str = Field(..., description="The original user query.")
    answer: str = Field(..., description="The agent's final answer.")
    tool_calls: list[ToolCallLog] = Field(
        default_factory=list,
        description="Ordered list of tool calls made during this run.",
    )
    iterations: int = Field(..., description="Number of LangGraph iterations executed.")
    elapsed_seconds: float = Field(..., description="Wall-clock time for the run.")


class StreamEvent(BaseModel):
    """A single SSE event yielded by GET /api/v1/agent/stream."""

    event: Literal["token", "tool_start", "tool_end", "done", "error"]
    data: str
    session_id: str | None = None


class HealthResponse(BaseModel):
    """Response for GET /health/ready."""

    status: Literal["ok", "degraded"] = Field(
        ..., description="'ok' if all dependencies are reachable, 'degraded' otherwise."
    )
    version: str = Field(..., description="Application version.")
    ollama_reachable: bool = Field(..., description="Whether the Ollama API responded.")
    redis_reachable: bool = Field(..., description="Whether Redis responded to PING.")
