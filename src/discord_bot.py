"""Discord bot implementation for Chorus system."""

import asyncio
import base64
import io
import logging
import random
from typing import Dict, List
from datetime import datetime
import discord
from discord.ext import commands

from src.config import BotConfig
from src.llm_client import get_llm_client
from src.memory import MemorySystem
from src.image_utils import process_discord_attachment

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

        # Process image attachments
        images = []
        if message.attachments:
            logger.info(f"[{self.config.name}] Message has {len(message.attachments)} attachment(s)")
            for attachment in message.attachments:
                try:
                    image_data = await process_discord_attachment(attachment)
                    if image_data:
                        images.append(image_data)
                        logger.info(f"[{self.config.name}] Processed image: {attachment.filename}")
                except Exception as e:
                    logger.error(f"[{self.config.name}] Error processing attachment: {e}", exc_info=True)

        # If no text but has images, add a default prompt
        if not text and images:
            text = "What's in this image?"

        logger.info(
            f"[{self.config.name}] Message from {sender} in {message.channel.name}: "
            f"{text[:50]}... (images: {len(images)})"
        )

        # Reset consecutive response counter when a HUMAN speaks
        # (Don't reset for bot messages - prevents bots from resetting each other's counters)
        if not message.author.bot:
            self._consecutive_responses[channel_id] = 0

        # Add to conversation history
        self.history.add_message(
            channel_id=channel_id,
            sender=sender,
            text=text,
            timestamp=message.created_at,
        )

        # Check if we should respond
        if await self._should_respond(message, has_images=len(images) > 0):
            await self._send_response(message, images=images)
        else:
            # Even if we don't respond, maybe react with an emoji
            await self._maybe_react(message)

    async def _should_respond(self, message: discord.Message, has_images: bool = False) -> bool:
        """Determine if the bot should respond to this message.

        Args:
            message: Discord message
            has_images: Whether the message contains images

        Returns:
            True if bot should respond
        """
        text = message.content.lower()
        channel_id = str(message.channel.id)
        sender = message.author.display_name or message.author.name

        # Only respond to images if bot supports vision
        if has_images and self.config.supports_vision:
            logger.info(f"[{self.config.name}] Message has images and bot supports vision - will respond")
            return True
        elif has_images and not self.config.supports_vision:
            logger.info(f"[{self.config.name}] Message has images but bot doesn't support vision - will skip auto-response")
            # Don't auto-respond, but continue with normal decision logic

        # Check for direct mention (always respond)
        if self.user.mentioned_in(message):
            logger.info(f"[{self.config.name}] Direct mention detected - will respond")
            return True

        # Check if bot name is in message (always respond)
        if self.config.name.lower() in text:
            logger.info(f"[{self.config.name}] Bot name found in message - will respond")
            return True

        # Also check Discord display name (e.g., "Sonnet" for "Chorus Sonnet")
        # BUT: Skip this check for messages from other bots to prevent feedback loops
        if self.user and self.user.display_name and not message.author.bot:
            display_name_lower = self.user.display_name.lower()
            # Check both full display name and parts of it
            for name_part in display_name_lower.split():
                if name_part in text:
                    logger.info(f"[{self.config.name}] Display name '{name_part}' found in message - will respond")
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

    def _split_message(self, text: str, max_length: int = 2000) -> List[str]:
        """Split a message into chunks that fit Discord's character limit.

        Args:
            text: The message text to split
            max_length: Maximum length per chunk (default 2000 for Discord)

        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first (double newline)
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            # If adding this paragraph would exceed limit, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > max_length:
                chunks.append(current_chunk)
                current_chunk = ""

            # If paragraph itself is too long, split by sentences/lines
            if len(para) > max_length:
                lines = para.split('\n')
                for line in lines:
                    if len(line) > max_length:
                        # Split very long lines at word boundaries
                        words = line.split(' ')
                        for word in words:
                            if len(current_chunk) + len(word) + 1 > max_length:
                                chunks.append(current_chunk)
                                current_chunk = word
                            else:
                                current_chunk = current_chunk + ' ' + word if current_chunk else word
                    else:
                        if current_chunk and len(current_chunk) + len(line) + 1 > max_length:
                            chunks.append(current_chunk)
                            current_chunk = line
                        else:
                            current_chunk = current_chunk + '\n' + line if current_chunk else line
            else:
                current_chunk = current_chunk + '\n\n' + para if current_chunk else para

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text[:max_length]]

    async def _post_generated_images(
        self,
        channel: discord.TextChannel,
        image_data_urls: List[str]
    ) -> bool:
        """Post generated images to a Discord channel.

        Args:
            channel: Discord channel to post to
            image_data_urls: List of base64 data URLs (e.g., "data:image/png;base64,...")

        Returns:
            True if successfully posted
        """
        try:
            files = []

            for idx, data_url in enumerate(image_data_urls):
                try:
                    # Parse data URL format: data:image/png;base64,iVBORw0...
                    if not data_url.startswith("data:image/"):
                        logger.warning(f"Invalid data URL format: {data_url[:50]}...")
                        continue

                    # Extract MIME type and base64 data
                    header, base64_data = data_url.split(",", 1)
                    mime_type = header.split(":")[1].split(";")[0]  # e.g., "image/png"

                    # Get file extension from MIME type
                    ext = mime_type.split("/")[1]  # e.g., "png"

                    # Decode base64
                    image_bytes = base64.b64decode(base64_data)

                    # Create Discord file
                    filename = f"generated_image_{idx + 1}.{ext}"
                    file = discord.File(io.BytesIO(image_bytes), filename=filename)
                    files.append(file)

                    logger.info(f"Prepared {filename} ({len(image_bytes)} bytes)")

                except Exception as e:
                    logger.error(f"Error processing image {idx}: {e}", exc_info=True)
                    continue

            if files:
                await channel.send(files=files)
                logger.info(f"[{self.config.name}] Posted {len(files)} generated image(s)")
                return True
            else:
                logger.warning(f"[{self.config.name}] No valid images to post")
                return False

        except Exception as e:
            logger.error(f"[{self.config.name}] Error posting generated images: {e}", exc_info=True)
            return False

    async def _send_response(self, message: discord.Message, images: List[Dict] = None):
        """Send a response to the message.

        Args:
            message: Discord message to respond to
            images: Optional list of processed image dicts
        """
        channel_id = str(message.channel.id)
        text = message.content or "What's in this image?"  # Default if only images
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

        # Only send images to LLM if bot supports vision
        images_for_llm = images if self.config.supports_vision else None
        if images and not self.config.supports_vision:
            logger.info(f"[{self.config.name}] Ignoring {len(images)} image(s) - bot doesn't support vision")

        # Show typing indicator
        async with message.channel.typing():
            # Generate response using LLM (with or without tools)
            if tools:
                result = await self.llm_client.get_response_with_tools(
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
                    images=images_for_llm,
                )
                # Extract text and generated images from result
                if result:
                    response_text = result.get("text")
                    generated_images = result.get("generated_images", [])
                else:
                    response_text = None
                    generated_images = []
            else:
                response_text = await self.llm_client.get_response(
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
                    images=images_for_llm,
                )
                generated_images = []

        if response_text:
            # Send text response (split if needed for Discord's 2000 char limit)
            for chunk in self._split_message(response_text):
                await message.channel.send(chunk)

            # Post any generated images
            if generated_images:
                logger.info(f"[{self.config.name}] Posting {len(generated_images)} generated image(s)")
                await self._post_generated_images(message.channel, generated_images)

            # Add our response to history
            self.history.add_message(
                channel_id=channel_id,
                sender=self.config.name,
                text=response_text,
            )

            # Track consecutive responses
            self._consecutive_responses[channel_id] = self._consecutive_responses.get(channel_id, 0) + 1

            logger.info(f"[{self.config.name}] Sent response: {response_text[:50]}...")

            # Extract and store new memories from this conversation
            # Do this asynchronously without blocking
            asyncio.create_task(
                self._process_and_store_memories(channel_id, response_text)
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
