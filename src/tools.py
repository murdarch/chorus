"""Tool definitions and implementations for LLM function calling."""

import logging
from typing import Optional, Dict, Any, List
from tavily import TavilyClient

from src.config import get_settings

logger = logging.getLogger(__name__)


class SearchTool:
    """Web search tool using Tavily API."""

    def __init__(self):
        """Initialize the search tool."""
        settings = get_settings()
        self.tavily_api_key = settings.tavily_api_key

        if self.tavily_api_key:
            self.client = TavilyClient(api_key=self.tavily_api_key)
            self.enabled = True
            logger.info("Initialized Tavily search tool")
        else:
            self.client = None
            self.enabled = False
            logger.warning("Tavily API key not found - search tool disabled")

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> Dict[str, Any]:
        """Perform a web search.

        Args:
            query: The search query
            max_results: Maximum number of results to return
            search_depth: "basic" or "advanced" search depth

        Returns:
            Dictionary containing search results
        """
        if not self.enabled:
            return {
                "error": "Search tool not available - Tavily API key not configured"
            }

        try:
            logger.info(f"Performing Tavily search: {query}")

            # Perform search
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_answer=True,
                include_raw_content=False,
            )

            # Format results for LLM
            formatted_results = {
                "query": query,
                "answer": response.get("answer", ""),
                "results": [],
            }

            for result in response.get("results", []):
                formatted_results["results"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                })

            logger.info(f"Search returned {len(formatted_results['results'])} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            return {"error": f"Search failed: {str(e)}"}


# Tool definition for OpenRouter function calling
TAVILY_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information, news, facts, or answers to questions. "
            "Use this when you need up-to-date information that may not be in your training data, "
            "or when the user asks about recent events, current facts, or real-time information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return (1-10)",
                    "default": 5,
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "Search depth: 'basic' for quick results, 'advanced' for thorough search",
                    "default": "basic",
                },
            },
            "required": ["query"],
        },
    },
}


# Global search tool instance
_search_tool: Optional[SearchTool] = None


def get_search_tool() -> SearchTool:
    """Get or create the global search tool instance."""
    global _search_tool
    if _search_tool is None:
        _search_tool = SearchTool()
    return _search_tool


def get_available_tools() -> List[Dict[str, Any]]:
    """Get list of available tool definitions."""
    tools = []

    # Add Tavily search if available
    search_tool = get_search_tool()
    if search_tool.enabled:
        tools.append(TAVILY_SEARCH_TOOL)

    return tools
