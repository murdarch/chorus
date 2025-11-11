"""OpenRouter LLM client for Chorus bot system."""

import logging
from typing import List, Dict, Optional
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
    ) -> bool:
        """Determine if the bot should respond to a message.

        Uses the LLM to make an intelligent decision about participation.

        Args:
            model: Model identifier
            conversation_history: Recent conversation history
            bot_name: Name of this bot
            current_message: The current message text
            sender: Name of the message sender

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
            for msg in conversation_history[-5:]:  # Last 5 messages for context
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
                max_tokens=10,
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

    async def get_response(
        self,
        model: str,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        current_message: str,
        sender: str,
        bot_name: str,
        memories: Optional[List[str]] = None,
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

            # Add conversation history
            for msg in conversation_history[-10:]:  # Last 10 messages
                # Determine role based on sender
                role = "assistant" if msg["sender"] == bot_name else "user"

                # Format message with sender name if it's from user
                if role == "user":
                    content = f"{msg['sender']}: {msg['text']}"
                else:
                    content = msg["text"]

                messages.append({"role": role, "content": content})

            # Add current message
            messages.append({
                "role": "user",
                "content": f"{sender}: {current_message}"
            })

            logger.info(f"Generating response for {bot_name} to message from {sender}")

            # Get completion
            response = await self.get_completion(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )

            return response

        except Exception as e:
            logger.error(f"Error getting response: {e}", exc_info=True)
            return None


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
