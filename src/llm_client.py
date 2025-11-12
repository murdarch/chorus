"""OpenRouter LLM client for Chorus bot system."""

import json
import logging
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI

from src.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with OpenRouter API."""

    def __init__(self):
        """Initialize the LLM client."""
        settings = get_settings()

        # Create AsyncOpenAI client pointing to OpenRouter
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        logger.info("Initialized LLM client with OpenRouter")

    async def get_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        """Get a completion from the LLM.

        Args:
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            The LLM's response text, or None if error
        """
        try:
            logger.debug(f"Requesting completion from {model}")
            logger.debug(f"Messages: {messages}")

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            logger.debug(f"Got response: {content[:100]}...")

            return content

        except Exception as e:
            logger.error(f"Error getting completion from {model}: {e}", exc_info=True)
            return None

    async def should_respond(
        self,
        model: str,
        conversation_history: List[Dict[str, str]],
        bot_name: str,
        current_message: str,
        sender: str,
        max_decision_context: int = 5,
        max_tokens_decision: int = 10,
    ) -> bool:
        """Determine if the bot should respond to a message.

        Uses the LLM to make an intelligent decision about participation.

        Args:
            model: Model identifier
            conversation_history: Recent conversation history
            bot_name: Name of this bot
            current_message: The current message text
            sender: Name of the message sender
            max_decision_context: Number of recent messages to use for context
            max_tokens_decision: Maximum tokens for decision response

        Returns:
            True if bot should respond
        """
        try:
            # Build prompt for decision
            system_prompt = f"""You are {bot_name}, deciding whether to participate in a conversation.

Consider:
- Is the message directed at you?
- Is it a question you can help with?
- Would your response add value?
- Have you spoken recently? (Don't dominate the conversation)

Respond with ONLY "yes" or "no"."""

            # Format conversation for context
            context_lines = []
            for msg in conversation_history[-max_decision_context:]:  # Use configurable context
                context_lines.append(f"{msg['sender']}: {msg['text']}")

            context_lines.append(f"{sender}: {current_message}")
            context = "\n".join(context_lines)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Recent conversation:\n{context}\n\nShould you respond?"},
            ]

            # Use lower temperature for more consistent decisions
            response = await self.get_completion(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens_decision,
            )

            if response:
                decision = response.strip().lower()
                should_respond = "yes" in decision
                logger.info(
                    f"LLM decision for {bot_name}: {'RESPOND' if should_respond else 'SKIP'} "
                    f"(raw: {decision})"
                )
                return should_respond

            # Default to not responding if LLM fails
            logger.warning(f"No response from LLM, defaulting to not respond")
            return False

        except Exception as e:
            logger.error(f"Error in should_respond: {e}", exc_info=True)
            return False

    async def get_reaction(
        self,
        model: str,
        message: str,
        sender: str,
        bot_name: str,
    ) -> Optional[str]:
        """Determine if bot should react with an emoji, and which one.

        Args:
            model: Model identifier
            message: The message to react to
            sender: Name of the message sender
            bot_name: Name of this bot

        Returns:
            Emoji string to react with, or None if no reaction
        """
        try:
            system_prompt = f"""You are {bot_name}. Decide if you should react to this message with an emoji.

Available reactions: ❤️ 👍 😄 🎉 🤔 👀 🚀 💡 ✅

Guidelines:
- React to positive/helpful messages with ❤️ 👍 🎉
- React to questions/problems with 🤔 💡
- React to interesting insights with 👀 💡
- React to achievements/completions with ✅ 🎉 🚀
- React to funny messages with 😄
- Don't react to every message

Respond with ONLY the emoji, or "none" if no reaction."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{sender}: {message}\n\nShould you react? If yes, which emoji?"},
            ]

            response = await self.get_completion(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=10,
            )

            if response:
                reaction = response.strip()
                if reaction == "none" or "none" in reaction.lower():
                    return None

                # Extract emoji from response
                valid_emojis = ["❤️", "👍", "😄", "🎉", "🤔", "👀", "🚀", "💡", "✅"]
                for emoji in valid_emojis:
                    if emoji in reaction:
                        logger.info(f"{bot_name} will react with {emoji}")
                        return emoji

            return None

        except Exception as e:
            logger.error(f"Error in get_reaction: {e}", exc_info=True)
            return None

    def _build_message_content(
        self,
        text: str,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """Build message content that supports both text and images.

        Args:
            text: Text content
            images: Optional list of image dicts from image_utils

        Returns:
            Either a string (text only) or a list of content items (multi-modal)
        """
        if not images:
            return text

        # Multi-modal format: [{"type": "text", "text": "..."}, {"type": "image_url", ...}]
        content = [{"type": "text", "text": text}]
        content.extend(images)
        return content

    async def get_response(
        self,
        model: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        current_message: str,
        sender: str,
        bot_name: str,
        memories: Optional[List[str]] = None,
        summaries: Optional[List[str]] = None,
        max_context_messages: int = 10,
        max_tokens_response: int = 500,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """Generate a conversational response.

        Args:
            model: Model identifier
            system_prompt: System prompt defining bot behavior
            conversation_history: Recent conversation history
            current_message: The current message to respond to
            sender: Name of the message sender
            bot_name: Name of this bot
            memories: Optional list of relevant memories to include
            summaries: Optional list of conversation summaries to include
            max_context_messages: Number of recent messages to include in context
            max_tokens_response: Maximum tokens for response
            images: Optional list of image dicts for vision input

        Returns:
            The bot's response text, or None if error
        """
        try:
            # Build enhanced system prompt with memories
            enhanced_system = system_prompt

            if memories:
                memory_text = "\n".join(f"- {m}" for m in memories)
                enhanced_system += f"\n\nRelevant memories:\n{memory_text}"

            # Build messages list
            messages = [{"role": "system", "content": enhanced_system}]

            # Add summaries of older conversation if available
            if summaries:
                for summary in summaries:
                    messages.append({
                        "role": "system",
                        "content": f"Previous conversation summary: {summary}"
                    })

            # Add conversation history
            for msg in conversation_history[-max_context_messages:]:  # Use configurable context
                # Determine role based on sender
                role = "assistant" if msg["sender"] == bot_name else "user"

                # Format message with sender name if it's from user
                if role == "user":
                    content = f"{msg['sender']}: {msg['text']}"
                else:
                    content = msg["text"]

                messages.append({"role": role, "content": content})

            # Add current message (with optional images)
            current_content = self._build_message_content(
                f"{sender}: {current_message}",
                images
            )
            messages.append({
                "role": "user",
                "content": current_content
            })

            if images:
                logger.info(
                    f"Generating response for {bot_name} to message from {sender} "
                    f"with {len(images)} image(s)"
                )
            else:
                logger.info(f"Generating response for {bot_name} to message from {sender}")

            # Get completion
            response = await self.get_completion(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens_response,
            )

            return response

        except Exception as e:
            logger.error(f"Error getting response: {e}", exc_info=True)
            return None

    async def get_response_with_tools(
        self,
        model: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        current_message: str,
        sender: str,
        bot_name: str,
        memories: Optional[List[str]] = None,
        summaries: Optional[List[str]] = None,
        max_context_messages: int = 10,
        max_tokens_response: int = 500,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tool_rounds: int = 3,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate a conversational response with tool calling support.

        Args:
            model: Model identifier
            system_prompt: System prompt defining bot behavior
            conversation_history: Recent conversation history
            current_message: The current message to respond to
            sender: Name of the message sender
            bot_name: Name of this bot
            memories: Optional list of relevant memories to include
            summaries: Optional list of conversation summaries to include
            max_context_messages: Number of recent messages to include in context
            max_tokens_response: Maximum tokens for response
            tools: Optional list of tool definitions for function calling
            max_tool_rounds: Maximum number of tool call rounds (default: 3)
            images: Optional list of image dicts for vision input

        Returns:
            Dict with 'text' and 'generated_images' keys, or None if error
        """
        try:
            # If no tools provided, fall back to regular response
            if not tools:
                response = await self.get_response(
                    model=model,
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    current_message=current_message,
                    sender=sender,
                    bot_name=bot_name,
                    memories=memories,
                    summaries=summaries,
                    max_context_messages=max_context_messages,
                    max_tokens_response=max_tokens_response,
                    images=images,
                )
                return {"text": response, "generated_images": []} if response else None

            # Build enhanced system prompt with memories
            enhanced_system = system_prompt
            if memories:
                memory_text = "\n".join(f"- {m}" for m in memories)
                enhanced_system += f"\n\nRelevant memories:\n{memory_text}"

            # Build initial messages list
            messages = [{"role": "system", "content": enhanced_system}]

            # Add summaries of older conversation if available
            if summaries:
                for summary in summaries:
                    messages.append({
                        "role": "system",
                        "content": f"Previous conversation summary: {summary}"
                    })

            # Add conversation history
            for msg in conversation_history[-max_context_messages:]:
                role = "assistant" if msg["sender"] == bot_name else "user"
                if role == "user":
                    content = f"{msg['sender']}: {msg['text']}"
                else:
                    content = msg["text"]
                messages.append({"role": role, "content": content})

            # Add current message (with optional images)
            current_content = self._build_message_content(
                f"{sender}: {current_message}",
                images
            )
            messages.append({
                "role": "user",
                "content": current_content
            })

            # Import tools module here to avoid circular imports
            from src.tools import get_search_tool, get_image_gen_tool

            search_tool = get_search_tool()
            image_gen_tool = get_image_gen_tool()

            # Track generated images
            generated_images = []

            # Tool calling loop
            for round_num in range(max_tool_rounds):
                logger.info(f"LLM call round {round_num + 1} for {bot_name}")

                # Make API call with tools
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens_response,
                    tools=tools,
                    tool_choice="auto",
                )

                choice = response.choices[0]
                finish_reason = choice.finish_reason

                # If the model returned a text response (no tool call), we're done
                if finish_reason == "stop" or not choice.message.tool_calls:
                    content = choice.message.content
                    if content:
                        logger.info(f"Final response from {bot_name} with {len(generated_images)} generated image(s)")
                        return {
                            "text": content,
                            "generated_images": generated_images
                        }
                    else:
                        logger.warning("Model returned no content")
                        return None

                # Handle tool calls
                if finish_reason == "tool_calls" and choice.message.tool_calls:
                    logger.info(f"Model requested {len(choice.message.tool_calls)} tool call(s)")

                    # Add assistant message with tool calls to conversation
                    messages.append({
                        "role": "assistant",
                        "content": choice.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            }
                            for tc in choice.message.tool_calls
                        ]
                    })

                    # Execute each tool call
                    for tool_call in choice.message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        logger.info(f"Executing tool: {function_name} with args: {function_args}")

                        # Execute the tool
                        if function_name == "web_search":
                            tool_result = await search_tool.search(**function_args)
                        elif function_name == "generate_image":
                            tool_result = await image_gen_tool.generate_image(**function_args)
                            # Collect generated images
                            if tool_result.get("success") and tool_result.get("images"):
                                generated_images.extend(tool_result["images"])
                                logger.info(f"Collected {len(tool_result['images'])} generated image(s)")
                        else:
                            tool_result = {"error": f"Unknown tool: {function_name}"}

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        })

                        logger.info(f"Tool result: {str(tool_result)[:200]}...")

                    # Continue loop to get final response with tool results
                    continue

                # If we get here, something unexpected happened
                logger.warning(f"Unexpected finish_reason: {finish_reason}")
                content = choice.message.content if choice.message.content else None
                return {"text": content, "generated_images": generated_images} if content else None

            # Max rounds reached
            logger.warning(f"Max tool rounds ({max_tool_rounds}) reached")
            return {
                "text": "I'm sorry, I encountered an issue while processing your request with multiple tool calls.",
                "generated_images": generated_images
            }

        except Exception as e:
            logger.error(f"Error in get_response_with_tools: {e}", exc_info=True)
            return None

    async def summarize_conversation(
        self,
        model: str,
        messages: List[Dict[str, str]],
        bot_name: str,
        max_tokens: int = 200,
    ) -> Optional[str]:
        """Summarize a chunk of conversation history.

        Args:
            model: Model identifier
            messages: List of messages to summarize
            bot_name: Name of this bot
            max_tokens: Maximum tokens for summary

        Returns:
            A concise summary of the conversation, or None if error
        """
        try:
            if not messages:
                return None

            logger.info(f"Summarizing {len(messages)} messages for {bot_name}")

            # Build context from messages
            conversation_text = []
            for msg in messages:
                sender = msg.get("sender", "Unknown")
                text = msg.get("text", "")
                conversation_text.append(f"{sender}: {text}")

            conversation_str = "\n".join(conversation_text)

            # Request summary
            summary_prompt = f"""Summarize this conversation in 2-3 sentences, focusing on key topics discussed and any important decisions or information exchanged:

{conversation_str}

Provide a concise summary:"""

            response = await self.get_completion(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise conversation summaries."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )

            if response:
                logger.info(f"Created summary: {response[:100]}...")
                return response.strip()

            return None

        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}", exc_info=True)
            return None


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
