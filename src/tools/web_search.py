"""Web search tool using Tavily API."""

from dataclasses import dataclass

from tavily import TavilyClient

from src.config import get_config


@dataclass
class WebResult:
    """A web search result."""

    title: str
    url: str
    content: str
    score: float


async def web_search(query: str, max_results: int = 5) -> list[WebResult]:
    """
    Search the web for relevant context using Tavily.

    Args:
        query: The search query
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of WebResult objects with title, URL, content, and relevance score
    """
    config = get_config()
    client = TavilyClient(api_key=config.tavily_api_key)

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
    )

    results = []
    for r in response.get("results", []):
        results.append(
            WebResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
            )
        )

    return results


def _format_results_for_agent(results: list[WebResult]) -> str:
    """Format web results as a string for the agent."""
    if not results:
        return "No web results found."

    lines = []
    for r in results:
        lines.append(f"- [{r.title}]({r.url}): {r.content[:200]}...")
    return "\n".join(lines)
