import asyncio

from duckduckgo_search import DDGS
from langchain_core.tools import tool


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return formatted results.

    Use this skill to retrieve current, factual information that may be
    beyond the LLM's training data. Always cite the returned sources
    in your final answer.

    Args:
        query:       The search query. Be specific for best results.
        max_results: Maximum number of results to return (default 5, max 10).

    Returns:
        Formatted search results with title, URL, and snippet per result.
        Returns an error message if the search fails.
    """
    max_results = min(max_results, 10)  # hard cap to avoid abuse

    try:
        raw: list[dict[str, str]] = await asyncio.to_thread(
            lambda: list(DDGS().text(query, max_results=max_results))
        )
    except Exception as exc:
        return f"[web_search error] DuckDuckGo query failed: {exc}"

    if not raw:
        return f"[web_search] No results found for query: {query!r}"

    lines: list[str] = [f"Search results for: {query!r}\n"]
    for i, result in enumerate(raw, start=1):
        title = result.get("title", "No title")
        href = result.get("href", "")
        body = result.get("body", "No snippet available.")
        lines.append(f"{i}. **{title}**\n   URL: {href}\n   {body}\n")

    return "\n".join(lines)
