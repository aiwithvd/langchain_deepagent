---
name: web_search
description: Search the web using DuckDuckGo for current, factual, up-to-date information
---

# Web Search Skill

## When to Use
Call the `web_search` tool when you need:
- Current events or recent developments (post knowledge cutoff)
- Factual data that must be verified from external sources
- Statistics, prices, or rapidly changing information
- Multiple perspectives on a topic

## How to Search Effectively

### Query Formulation
- Be **specific**: `"LangGraph 2025 streaming SSE tutorial"` not `"langchain"`
- Use **quotes** for exact phrases: `"chain of thought" prompting technique`
- Add **year** for recency: `"fastapi rate limiting redis 2025"`
- Use **site:** for trusted sources: `site:docs.python.org asyncio`

### Processing Results
1. Run 2-3 targeted searches rather than one broad one
2. Cross-reference information across multiple results
3. Prefer official docs, GitHub repos, and reputable publications
4. Discard results older than 2 years for fast-moving topics

## Output Format

Always present search results as:

```
**Source:** [Title](URL)
**Summary:** <1-2 sentence summary of what this source says>

**Source:** [Title](URL)
**Summary:** <1-2 sentence summary>
```

Then synthesize:
```
**Synthesis:** <combined insight from all sources>
```

## Rules
- Never fabricate URLs — only use URLs from actual search results
- Always cite your sources in the final answer
- If results conflict, note the discrepancy and prefer the most recent
- Maximum `max_results=5` per query for performance
