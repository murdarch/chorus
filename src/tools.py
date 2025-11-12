"""Tool definitions and implementations for LLM function calling."""

import logging
from typing import Optional, Dict, Any, List
from tavily import TavilyClient
from openai import AsyncOpenAI

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


class ImageGenerationTool:
    """Image generation tool using OpenRouter API."""

    def __init__(self):
        """Initialize the image generation tool."""
        settings = get_settings()
        self.openrouter_api_key = settings.openrouter_api_key

        if self.openrouter_api_key:
            self.client = AsyncOpenAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            self.enabled = True
            # Default to Gemini 2.5 Flash for image generation
            self.default_model = "google/gemini-2.5-flash-image-preview"
            logger.info("Initialized image generation tool")
        else:
            self.client = None
            self.enabled = False
            logger.warning("OpenRouter API key not found - image generation disabled")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an image from a text prompt.

        Args:
            prompt: Description of the image to generate
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            model: Optional model override

        Returns:
            Dictionary containing image data or error
        """
        if not self.enabled:
            return {
                "error": "Image generation not available - OpenRouter API key not configured"
            }

        try:
            model_to_use = model or self.default_model
            logger.info(f"Generating image with {model_to_use}: {prompt[:100]}...")

            # Make API call
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                modalities=["image", "text"],
                extra_body={
                    "image_config": {
                        "aspect_ratio": aspect_ratio
                    }
                }
            )

            # Parse response
            message = response.choices[0].message

            # Check for images in response
            images = getattr(message, 'images', None) or []

            if not images:
                logger.warning("No images in generation response")
                return {
                    "success": False,
                    "error": "Model did not generate an image",
                    "text_response": message.content or ""
                }

            # Extract image data URLs
            image_urls = []
            for img in images:
                if hasattr(img, 'image_url') and hasattr(img.image_url, 'url'):
                    image_urls.append(img.image_url.url)
                elif isinstance(img, dict) and 'image_url' in img:
                    image_urls.append(img['image_url']['url'])

            logger.info(f"Successfully generated {len(image_urls)} image(s)")

            return {
                "success": True,
                "images": image_urls,
                "text": message.content or "",
                "model": model_to_use,
                "prompt": prompt,
            }

        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Image generation failed: {str(e)}"
            }


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

IMAGE_GENERATION_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": (
            "Generate an image from a text description. Use this when the user explicitly asks "
            "to create, draw, generate, or visualize an image. You can also proactively offer "
            "to generate images when it would enhance the conversation (e.g., creating diagrams, "
            "illustrations, or visual examples)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the image to generate. Be specific and descriptive. "
                        "Include details about style, composition, colors, mood, etc."
                    ),
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"],
                    "description": "Aspect ratio of the generated image",
                    "default": "1:1",
                },
            },
            "required": ["prompt"],
        },
    },
}


# Global tool instances
_search_tool: Optional[SearchTool] = None
_image_gen_tool: Optional[ImageGenerationTool] = None


def get_search_tool() -> SearchTool:
    """Get or create the global search tool instance."""
    global _search_tool
    if _search_tool is None:
        _search_tool = SearchTool()
    return _search_tool


def get_image_gen_tool() -> ImageGenerationTool:
    """Get or create the global image generation tool instance."""
    global _image_gen_tool
    if _image_gen_tool is None:
        _image_gen_tool = ImageGenerationTool()
    return _image_gen_tool


def get_available_tools() -> List[Dict[str, Any]]:
    """Get list of available tool definitions."""
    tools = []

    # Add Tavily search if available
    search_tool = get_search_tool()
    if search_tool.enabled:
        tools.append(TAVILY_SEARCH_TOOL)

    # Add image generation if available
    image_gen_tool = get_image_gen_tool()
    if image_gen_tool.enabled:
        tools.append(IMAGE_GENERATION_TOOL)

    return tools
