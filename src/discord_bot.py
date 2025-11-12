"""Discord bot implementation for Chorus system."""

import asyncio
import logging
import random
from typing import Dict, List
from datetime import datetime
import discord
from discord.ext import commands

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

        # Store messages per channel ID
        self._histories: Dict[str, List[Dict]] = {}
        # Store summaries per channel ID
        self._summaries: Dict[str, List[str]] = {}
        # Track if summarization is in progress
        self._summarizing: Dict[str, bool] = {}

    def add_message(self, channel_id: str, sender: str, text: str, timestamp: datetime = None):
        """Add a message to conversation history.

        Args:
            channel_id: Unique channel identifier
            sender: Name/ID of message sender
            text: Message content
            timestamp: Message timestamp (defaults to now)
        """
        if channel_id not in self._histories:
            self._histories[channel_id] = []
            self._summaries[channel_id] = []

        message = {
            "sender": sender,
            "text": text,
            "timestamp": timestamp or datetime.utcnow(),
        }

        history = self._histories[channel_id]
        history.append(message)

        # Keep only the most recent messages
        if len(history) > self.max_messages:
            self._histories[channel_id] = history[-self.max_messages:]

        # Check if we need to summarize
        if (self.llm_client and self.model and
            len(history) > self.max_verbatim_messages and
            not self._summarizing.get(channel_id, False)):

            # Trigger async summarization
            asyncio.create_task(self._auto_summarize(channel_id))

    def get_history(self, channel_id: str) -> List[Dict]:
        """Get conversation history for a specific channel.

        Args:
            channel_id: Unique channel identifier

        Returns:
            List of message dictionaries
        """
        return self._histories.get(channel_id, [])

    def get_summaries(self, channel_id: str) -> List[str]:
        """Get conversation summaries for a specific channel.

        Args:
            channel_id: Unique channel identifier

        Returns:
            List of summary strings
        """
        return self._summaries.get(channel_id, [])

    async def _auto_summarize(self, channel_id: str):
        """Automatically summarize older messages in a conversation.

        Args:
            channel_id: Unique channel identifier
        """
        try:
            # Mark as summarizing to prevent concurrent summarization
            self._summarizing[channel_id] = True

            history = self._histories.get(channel_id, [])
            if len(history) <= self.max_verbatim_messages:
                return

            # Calculate how many messages to summarize
            messages_to_summarize_count = len(history) - self.max_verbatim_messages

            # Get the messages to summarize
            messages_to_summarize = history[:messages_to_summarize_count]

            logger.info(
                f"[{self.bot_name}] Auto-summarizing {messages_to_summarize_count} messages "
                f"for channel {channel_id}"
            )

            # Create summary
            summary = await self.llm_client.summarize_conversation(
                model=self.model,
                messages=messages_to_summarize,
                bot_name=self.bot_name,
            )

            if summary:
                # Add summary to list
                if channel_id not in self._summaries:
                    self._summaries[channel_id] = []

                self._summaries[channel_id].append(summary)

                # Keep only the verbatim messages
                self._histories[channel_id] = history[messages_to_summarize_count:]

                logger.info(
                    f"[{self.bot_name}] Created summary for channel {channel_id}: "
                    f"{summary[:100]}..."
                )

        except Exception as e:
            logger.error(f"Error during auto-summarization: {e}", exc_info=True)

        finally:
            self._summarizing[channel_id] = False


class ChorusDiscordBot(commands.Bot):
    """Discord bot for Chorus system."""

    def __init__(self, config: BotConfig):
        """Initialize the Discord bot.

        Args:
            config: Bot configuration
        """
        # Initialize Discord bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.reactions = True

        super().__init__(
            command_prefix="!",  # Can be anything, we'll use intelligent participation
            intents=intents,
            help_command=None,
        )

        self.config = config
        self.llm_client = get_llm_client()
        self.history = ConversationHistory(
            max_messages=config.max_messages,
            max_verbatim_messages=config.max_verbatim_messages,
            llm_client=self.llm_client,
            model=config.model,
            bot_name=config.name,
        )
        self._consecutive_responses: Dict[str, int] = {}  # Track consecutive responses per channel
        self.max_consecutive_responses = 10  # Allow up to 10 turns before yielding

        # Initialize memory system
        self.memory = MemorySystem(
            db_path=config.memory_db_path,
            bot_name=config.name,
            model_name=config.model,
        )

        logger.info(f"Initialized Discord bot: {config.name}")

    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"{self.config.name} is now online! Connected as {self.user}")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages.

        Args:
            message: Discord message object
        """
        # Ignore messages from self
        if message.author == self.user:
            return

        # Ignore messages from other bots (optional - comment out if you want bot-to-bot interaction)
        # if message.author.bot:
        #     return

        channel_id = str(message.channel.id)
        sender = message.author.display_name or message.author.name
        text = message.content

        logger.info(f"[{self.config.name}] Message from {sender} in {message.channel.name}: {text[:50]}...")

        # Reset consecutive response counter when someone else speaks
        # (This allows for natural back-and-forth)
        self._consecutive_responses[channel_id] = 0

        # Add to conversation history
        self.history.add_message(
            channel_id=channel_id,
            sender=sender,
            text=text,
            timestamp=message.created_at,
        )

        # Check if we should respond
        if await self._should_respond(message):
            await self._send_response(message)
        else:
            # Even if we don't respond, maybe react with an emoji
            await self._maybe_react(message)

    async def _should_respond(self, message: discord.Message) -> bool:
        """Determine if the bot should respond to this message.

        Args:
            message: Discord message

        Returns:
            True if bot should respond
        """
        text = message.content.lower()
        channel_id = str(message.channel.id)
        sender = message.author.display_name or message.author.name

        # Check for direct mention (always respond)
        if self.user.mentioned_in(message):
            logger.info(f"[{self.config.name}] Direct mention detected - will respond")
            return True

        # Check if bot name is in message (always respond)
        if self.config.name.lower() in text:
            logger.info(f"[{self.config.name}] Bot name found in message - will respond")
            return True

        # Check if we've responded too many times in a row
        consecutive_count = self._consecutive_responses.get(channel_id, 0)
        if consecutive_count >= self.max_consecutive_responses:
            logger.info(f"[{self.config.name}] Responded {consecutive_count} times in a row - yielding to avoid dominating")
            return False

        # Use LLM to decide
        history = self.history.get_history(channel_id)
        should_respond = await self.llm_client.should_respond(
            model=self.config.model,
            conversation_history=history,
            bot_name=self.config.name,
            current_message=message.content,
            sender=sender,
            max_decision_context=self.config.max_decision_context,
            max_tokens_decision=self.config.max_tokens_decision,
        )

        logger.info(f"[{self.config.name}] LLM decision: {'respond' if should_respond else 'skip'}")
        return should_respond

    async def _send_response(self, message: discord.Message):
        """Send a response to the message.

        Args:
            message: Discord message to respond to
        """
        channel_id = str(message.channel.id)
        text = message.content
        sender = message.author.display_name or message.author.name

        # Get conversation history and summaries
        history = self.history.get_history(channel_id)
        summaries = self.history.get_summaries(channel_id)

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

        # Show typing indicator
        async with message.channel.typing():
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
            await message.channel.send(response)

            # Add our response to history
            self.history.add_message(
                channel_id=channel_id,
                sender=self.config.name,
                text=response,
            )

            # Track consecutive responses
            self._consecutive_responses[channel_id] = self._consecutive_responses.get(channel_id, 0) + 1

            logger.info(f"[{self.config.name}] Sent response: {response[:50]}...")

            # Extract and store new memories from this conversation
            # Do this asynchronously without blocking
            asyncio.create_task(
                self._process_and_store_memories(channel_id, response)
            )
        else:
            logger.error(f"[{self.config.name}] Failed to generate response")
            await message.channel.send("Sorry, I'm having trouble responding right now.")

    async def _process_and_store_memories(self, channel_id: str, response: str):
        """Process conversation and store new memories.

        Args:
            channel_id: Channel ID
            response: Bot's response
        """
        try:
            # Get recent conversation history
            history = self.history.get_history(channel_id)

            # Extract and store memories
            await self.memory.process_for_memories(history, response)

        except Exception as e:
            logger.error(f"[{self.config.name}] Error processing memories: {e}")

    async def _maybe_react(self, message: discord.Message):
        """Maybe react to a message with an emoji.

        Args:
            message: Discord message to react to
        """
        # 30% chance to consider reacting
        if random.random() > 0.3:
            return

        sender = message.author.display_name or message.author.name
        text = message.content

        logger.info(f"[{self.config.name}] Considering emoji reaction to message from {sender}")

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
            logger.info(f"[{self.config.name}] Will react with {emoji} after {delay:.1f}s")
            await asyncio.sleep(delay)

            # Send reaction (Discord makes this super easy!)
            try:
                await message.add_reaction(emoji)
                logger.info(f"[{self.config.name}] ✅ Reacted with {emoji}")
            except discord.HTTPException as e:
                logger.warning(f"[{self.config.name}] Failed to add reaction {emoji}: {e}")
