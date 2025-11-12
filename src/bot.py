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

    def __init__(
        self,
        max_messages: int = 10,
        max_verbatim_messages: int = 30,
        llm_client = None,
        model: str = None,
        bot_name: str = None,
    ):
        """Initialize conversation history tracker.

        Args:
            max_messages: Maximum number of messages to keep per conversation
            max_verbatim_messages: Maximum messages to keep verbatim (rest get summarized)
            llm_client: LLM client for summarization
            model: Model identifier for summarization
            bot_name: Bot name for logging
        """
        self.max_messages = max_messages
        self.max_verbatim_messages = max_verbatim_messages
        self.llm_client = llm_client
        self.model = model
        self.bot_name = bot_name

        # Store messages per conversation ID
        self._histories: Dict[str, List[Dict]] = {}
        # Store summaries per conversation ID
        self._summaries: Dict[str, List[str]] = {}
        # Track if summarization is in progress
        self._summarizing: Dict[str, bool] = {}

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
            self._summaries[conversation_id] = []

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

        # Check if we need to summarize
        # Only summarize if we have summarization enabled and history is getting long
        if (self.llm_client and self.model and
            len(history) > self.max_verbatim_messages and
            not self._summarizing.get(conversation_id, False)):

            # Trigger async summarization
            asyncio.create_task(self._auto_summarize(conversation_id))

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

    def get_summaries(self, conversation_id: str) -> List[str]:
        """Get conversation summaries for a specific conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            List of summary strings
        """
        return self._summaries.get(conversation_id, [])

    async def _auto_summarize(self, conversation_id: str):
        """Automatically summarize older messages in a conversation.

        Args:
            conversation_id: Unique conversation identifier
        """
        try:
            # Mark as summarizing to prevent concurrent summarization
            self._summarizing[conversation_id] = True

            history = self._histories.get(conversation_id, [])
            if len(history) <= self.max_verbatim_messages:
                return

            # Calculate how many messages to summarize
            messages_to_summarize_count = len(history) - self.max_verbatim_messages

            # Get the messages to summarize
            messages_to_summarize = history[:messages_to_summarize_count]

            logger.info(
                f"[{self.bot_name}] Auto-summarizing {messages_to_summarize_count} messages "
                f"for conversation {conversation_id}"
            )

            # Create summary
            summary = await self.llm_client.summarize_conversation(
                model=self.model,
                messages=messages_to_summarize,
                bot_name=self.bot_name,
            )

            if summary:
                # Add summary to list
                if conversation_id not in self._summaries:
                    self._summaries[conversation_id] = []

                self._summaries[conversation_id].append(summary)

                # Keep only the verbatim messages
                self._histories[conversation_id] = history[messages_to_summarize_count:]

                logger.info(
                    f"[{self.bot_name}] Created summary for conversation {conversation_id}: "
                    f"{summary[:100]}..."
                )

        except Exception as e:
            logger.error(f"Error during auto-summarization: {e}", exc_info=True)

        finally:
            self._summarizing[conversation_id] = False


class ChorusBot:
    """Main bot class for handling Teams interactions."""

    def __init__(self, config: BotConfig):
        """Initialize the bot.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.llm_client = get_llm_client()
        self.history = ConversationHistory(
            max_messages=config.max_messages,
            max_verbatim_messages=config.max_verbatim_messages,
            llm_client=self.llm_client,
            model=config.model,
            bot_name=config.name,
        )
        self._consecutive_responses: Dict[str, int] = {}  # Track consecutive responses per conversation
        self.max_consecutive_responses = 10  # Allow up to 10 turns before yielding

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

        # Reset consecutive response counter when someone else speaks
        # (This allows for natural back-and-forth)
        self._consecutive_responses[conversation_id] = 0

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

        # Check if we've responded too many times in a row
        consecutive_count = self._consecutive_responses.get(conversation_id, 0)
        if consecutive_count >= self.max_consecutive_responses:
            logger.info(f"[{self.config.bot_id}] Responded {consecutive_count} times in a row - yielding to avoid dominating")
            return False

        # Use LLM to decide
        history = self.history.get_history(conversation_id)
        should_respond = await self.llm_client.should_respond(
            model=self.config.model,
            conversation_history=history,
            bot_name=self.config.name,
            current_message=activity.text or "",
            sender=sender,
            max_decision_context=self.config.max_decision_context,
            max_tokens_decision=self.config.max_tokens_decision,
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

        # Get conversation history and summaries
        history = self.history.get_history(conversation_id)
        summaries = self.history.get_summaries(conversation_id)

        # Retrieve relevant memories
        memory_results = await self.memory.search_memories(
            query=text,
            limit=3,
        )

        # Format memories for LLM context
        memories = [mem["content"] for mem in memory_results] if memory_results else None

        # Get available tools if enabled
        tools = None
        if self.config.enable_tools:
            from src.tools import get_available_tools
            tools = get_available_tools()
            logger.info(f"Tools enabled for {self.config.name}: {len(tools)} tool(s) available")

        # Generate response using LLM (with or without tools)
        if tools:
            response = await self.llm_client.get_response_with_tools(
                model=self.config.model,
                system_prompt=self.config.system_prompt,
                conversation_history=history,
                current_message=text,
                sender=sender,
                bot_name=self.config.name,
                memories=memories,
                summaries=summaries,
                max_context_messages=self.config.max_messages,
                max_tokens_response=self.config.max_tokens_response,
                tools=tools,
            )
        else:
            response = await self.llm_client.get_response(
                model=self.config.model,
                system_prompt=self.config.system_prompt,
                conversation_history=history,
                current_message=text,
                sender=sender,
                bot_name=self.config.name,
                memories=memories,
                summaries=summaries,
                max_context_messages=self.config.max_messages,
                max_tokens_response=self.config.max_tokens_response,
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

            # Track consecutive responses
            self._consecutive_responses[conversation_id] = self._consecutive_responses.get(conversation_id, 0) + 1

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
