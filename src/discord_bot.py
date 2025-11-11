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

    def __init__(self, max_messages: int = 10):
        """Initialize conversation history tracker.

        Args:
            max_messages: Maximum number of messages to keep per conversation
        """
        self.max_messages = max_messages
        # Store messages per channel ID
        self._histories: Dict[str, List[Dict]] = {}

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

    def get_history(self, channel_id: str) -> List[Dict]:
        """Get conversation history for a specific channel.

        Args:
            channel_id: Unique channel identifier

        Returns:
            List of message dictionaries
        """
        return self._histories.get(channel_id, [])


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
        self.history = ConversationHistory(max_messages=10)
        self.llm_client = get_llm_client()
        self._last_responder: Dict[str, str] = {}  # Track last responder per channel

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

        # Don't respond twice in a row in the same channel
        if self._last_responder.get(channel_id) == self.config.name:
            logger.info(f"[{self.config.name}] Just responded - skipping to avoid dominating")
            return False

        # Use LLM to decide
        history = self.history.get_history(channel_id)
        should_respond = await self.llm_client.should_respond(
            model=self.config.model,
            conversation_history=history,
            bot_name=self.config.name,
            current_message=message.content,
            sender=sender,
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

        # Get conversation history
        history = self.history.get_history(channel_id)

        # Retrieve relevant memories
        memory_results = await self.memory.search_memories(
            query=text,
            limit=3,
        )

        # Format memories for LLM context
        memories = [mem["content"] for mem in memory_results] if memory_results else None

        # Show typing indicator
        async with message.channel.typing():
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
            await message.channel.send(response)

            # Add our response to history
            self.history.add_message(
                channel_id=channel_id,
                sender=self.config.name,
                text=response,
            )

            # Track that we just responded
            self._last_responder[channel_id] = self.config.name

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
