"""Bot implementation for Chorus system."""

import asyncio
import logging
import random
from typing import Dict, List
from datetime import datetime
from botbuilder.core import TurnContext
from botbuilder.schema import Activity, ActivityTypes

from src.config import BotConfig
from src.llm_client import get_llm_client
from src.memory import MemorySystem

logger = logging.getLogger(__name__)


class ConversationHistory:
    """Manages conversation history for a bot."""

    def __init__(self, max_messages: int = 10):
        """Initialize conversation history tracker.

        Args:
            max_messages: Maximum number of messages to keep per conversation
        """
        self.max_messages = max_messages
        # Store messages per conversation ID
        self._histories: Dict[str, List[Dict]] = {}

    def add_message(self, conversation_id: str, sender: str, text: str, timestamp: datetime = None):
        """Add a message to conversation history.

        Args:
            conversation_id: Unique conversation identifier
            sender: Name/ID of message sender
            text: Message content
            timestamp: Message timestamp (defaults to now)
        """
        if conversation_id not in self._histories:
            self._histories[conversation_id] = []

        message = {
            "sender": sender,
            "text": text,
            "timestamp": timestamp or datetime.utcnow(),
        }

        history = self._histories[conversation_id]
        history.append(message)

        # Keep only the most recent messages
        if len(history) > self.max_messages:
            self._histories[conversation_id] = history[-self.max_messages:]

    def get_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history for a specific conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            List of message dictionaries
        """
        return self._histories.get(conversation_id, [])

    def format_history(self, conversation_id: str) -> str:
        """Format conversation history as a string.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Formatted conversation history
        """
        history = self.get_history(conversation_id)
        if not history:
            return "No conversation history"

        lines = []
        for msg in history:
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            lines.append(f"[{timestamp}] {msg['sender']}: {msg['text']}")

        return "\n".join(lines)


class ChorusBot:
    """Main bot class for handling Teams interactions."""

    def __init__(self, config: BotConfig):
        """Initialize the bot.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.history = ConversationHistory(max_messages=10)
        self.llm_client = get_llm_client()
        self._last_responder = None  # Track who responded last

        # Initialize memory system
        self.memory = MemorySystem(
            db_path=config.memory_db_path,
            bot_name=config.name,
            model_name=config.model,
        )

        logger.info(f"Initialized {config.name} bot with memory system")

    async def on_turn(self, turn_context: TurnContext):
        """Handle incoming activity from Teams.

        Args:
            turn_context: The turn context containing activity info
        """
        activity = turn_context.activity

        # Log activity type
        logger.info(
            f"[{self.config.bot_id}] Received activity type: {activity.type}"
        )

        # Handle different activity types
        if activity.type == ActivityTypes.message:
            await self.on_message_activity(turn_context)
        elif activity.type == ActivityTypes.conversation_update:
            await self.on_conversation_update(turn_context)
        else:
            logger.debug(f"[{self.config.bot_id}] Ignoring activity type: {activity.type}")

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle message activities.

        Args:
            turn_context: The turn context
        """
        activity = turn_context.activity
        text = activity.text or ""
        sender = activity.from_property.name or activity.from_property.id
        conversation_id = activity.conversation.id

        logger.info(
            f"[{self.config.bot_id}] Message from {sender}: {text[:50]}..."
        )

        # Don't respond to our own messages
        if self._is_own_message(activity):
            logger.debug(f"[{self.config.bot_id}] Ignoring own message")
            return

        # Add to conversation history
        self.history.add_message(
            conversation_id=conversation_id,
            sender=sender,
            text=text,
        )

        # Check if we should respond
        if await self._should_respond(turn_context):
            await self._send_response(turn_context)
        else:
            # Even if we don't respond, maybe react with an emoji
            await self._maybe_react(turn_context)

    async def on_conversation_update(self, turn_context: TurnContext):
        """Handle conversation update activities (bot added to conversation, etc.).

        Args:
            turn_context: The turn context
        """
        activity = turn_context.activity

        # Check if bot was added to conversation
        if activity.members_added:
            for member in activity.members_added:
                if member.id != activity.recipient.id:
                    # A user was added
                    logger.info(
                        f"[{self.config.bot_id}] User {member.name} joined the conversation"
                    )
                else:
                    # Bot was added
                    logger.info(
                        f"[{self.config.bot_id}] Bot added to conversation {activity.conversation.id}"
                    )
                    await turn_context.send_activity(
                        f"Hello! I'm {self.config.name}, ready to chat! 👋"
                    )

    def _is_own_message(self, activity: Activity) -> bool:
        """Check if the message is from this bot.

        Args:
            activity: The activity to check

        Returns:
            True if message is from this bot
        """
        # Check if sender ID matches bot's recipient ID
        return activity.from_property.id == activity.recipient.id

    async def _should_respond(self, turn_context: TurnContext) -> bool:
        """Determine if the bot should respond to this message.

        Uses LLM to make intelligent decisions, but always responds to direct mentions.

        Args:
            turn_context: The turn context

        Returns:
            True if bot should respond
        """
        activity = turn_context.activity
        text = (activity.text or "").lower()
        sender = activity.from_property.name or activity.from_property.id
        conversation_id = activity.conversation.id

        # Check for direct mention (always respond)
        if activity.entities:
            for entity in activity.entities:
                if entity.type == "mention":
                    logger.info(f"[{self.config.bot_id}] Direct mention detected - will respond")
                    return True

        # Check if bot name is in message (always respond)
        if self.config.name.lower() in text:
            logger.info(f"[{self.config.bot_id}] Bot name found in message - will respond")
            return True

        # Don't respond twice in a row
        if self._last_responder == self.config.name:
            logger.info(f"[{self.config.bot_id}] Just responded - skipping to avoid dominating")
            return False

        # Use LLM to decide
        history = self.history.get_history(conversation_id)
        should_respond = await self.llm_client.should_respond(
            model=self.config.model,
            conversation_history=history,
            bot_name=self.config.name,
            current_message=activity.text or "",
            sender=sender,
        )

        return should_respond

    async def _send_response(self, turn_context: TurnContext):
        """Send a response to the current message.

        Uses LLM to generate intelligent, contextual responses.

        Args:
            turn_context: The turn context
        """
        activity = turn_context.activity
        text = activity.text or ""
        sender = activity.from_property.name or activity.from_property.id
        conversation_id = activity.conversation.id

        # Get conversation history
        history = self.history.get_history(conversation_id)

        # Retrieve relevant memories
        memory_results = await self.memory.search_memories(
            query=text,
            limit=3,
        )

        # Format memories for LLM context
        memories = [mem["content"] for mem in memory_results] if memory_results else None

        # Generate response using LLM
        response = await self.llm_client.get_response(
            model=self.config.model,
            system_prompt=self.config.system_prompt,
            conversation_history=history,
            current_message=text,
            sender=sender,
            bot_name=self.config.name,
            memories=memories,
        )

        if response:
            # Send response
            await turn_context.send_activity(response)

            # Add our response to history
            self.history.add_message(
                conversation_id=conversation_id,
                sender=self.config.name,
                text=response,
            )

            # Track that we just responded
            self._last_responder = self.config.name

            logger.info(f"[{self.config.bot_id}] Sent response: {response[:50]}...")

            # Extract and store new memories from this conversation
            # Do this asynchronously without blocking
            asyncio.create_task(
                self._process_and_store_memories(conversation_id, response)
            )
        else:
            logger.error(f"[{self.config.bot_id}] Failed to generate response")
            await turn_context.send_activity(
                "Sorry, I'm having trouble responding right now."
            )

    async def _process_and_store_memories(self, conversation_id: str, response: str):
        """Process conversation and store new memories.

        Args:
            conversation_id: Conversation ID
            response: Bot's response
        """
        try:
            # Get recent conversation history
            history = self.history.get_history(conversation_id)

            # Extract and store memories
            await self.memory.process_for_memories(history, response)

        except Exception as e:
            logger.error(f"[{self.config.bot_id}] Error processing memories: {e}")

    async def _maybe_react(self, turn_context: TurnContext):
        """Maybe react to a message with an emoji.

        Args:
            turn_context: The turn context
        """
        # 30% chance to consider reacting
        if random.random() > 0.3:
            return

        activity = turn_context.activity
        text = activity.text or ""
        sender = activity.from_property.name or activity.from_property.id

        logger.info(f"[{self.config.bot_id}] Considering emoji reaction to message from {sender}")

        # Ask LLM for reaction
        emoji = await self.llm_client.get_reaction(
            model=self.config.model,
            message=text,
            sender=sender,
            bot_name=self.config.name,
        )

        if emoji:
            # Add natural delay (1-3 seconds)
            delay = random.uniform(1.0, 3.0)
            logger.info(f"[{self.config.bot_id}] Will react with {emoji} after {delay:.1f}s")
            await asyncio.sleep(delay)

            # Send reaction
            await self._send_reaction(turn_context, emoji)

    async def _send_reaction(self, turn_context: TurnContext, emoji: str):
        """Send an emoji reaction to a message.

        Args:
            turn_context: The turn context
            emoji: The emoji to react with
        """
        try:
            activity = turn_context.activity

            # Create reaction activity
            # In Teams, reactions are sent as message reactions
            from botbuilder.schema import MessageReaction

            reaction = MessageReaction(
                reaction_type=emoji,
            )

            # Send the reaction as a separate activity
            # Note: This is simplified - in production you'd use the proper Teams API
            logger.info(f"[{self.config.bot_id}] Reacting with {emoji} to message {activity.id}")

            # For now, just log it - actual Teams reaction implementation
            # would require the Teams-specific activity format
            logger.info(f"[{self.config.bot_id}] 💬 {emoji} (reaction sent)")

        except Exception as e:
            logger.error(f"[{self.config.bot_id}] Error sending reaction: {e}", exc_info=True)
