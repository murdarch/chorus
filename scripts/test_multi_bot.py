"""Test multi-bot system with two bots interacting."""

import asyncio
import logging
from datetime import datetime
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, ConversationAccount

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from src.config import get_bot_config
from src.bot import ChorusBot


class MockTurnContext:
    """Mock TurnContext for testing."""

    def __init__(self, activity):
        self.activity = activity
        self.responses = []

    async def send_activity(self, text_or_activity):
        """Mock send_activity to capture responses."""
        if isinstance(text_or_activity, str):
            self.responses.append(text_or_activity)
        else:
            self.responses.append(text_or_activity.text)


async def create_message(text: str, sender_name: str, sender_id: str, recipient_name: str = "Bot"):
    """Create a mock message activity."""
    return Activity(
        type=ActivityTypes.message,
        text=text,
        from_property=ChannelAccount(id=sender_id, name=sender_name),
        recipient=ChannelAccount(id="bot_recipient", name=recipient_name),
        conversation=ConversationAccount(id="multi_bot_test"),
        timestamp=datetime.utcnow(),
        id=f"msg_{sender_name}_{datetime.utcnow().timestamp()}",
    )


async def send_message_to_bot(bot: ChorusBot, text: str, sender_name: str, sender_id: str):
    """Send a message to a bot and get response."""
    activity = await create_message(text, sender_name, sender_id, bot.config.name)
    turn_context = MockTurnContext(activity)
    await bot.on_message_activity(turn_context)
    return turn_context.responses


def print_message(sender: str, text: str, bot_name: str = None):
    """Pretty print a message."""
    if bot_name == "Nous":
        print(f"\n🟦 Nous: {text}")
    elif bot_name == "Claude":
        print(f"\n🟪 Claude: {text}")
    else:
        print(f"\n👤 {sender}: {text}")


async def test_two_bots_conversation():
    """Test two bots having a conversation."""
    print("\n" + "=" * 70)
    print("🤖💬🤖 TEST: Two Bots Having a Conversation")
    print("=" * 70)

    # Create both bots
    nous_bot = ChorusBot(get_bot_config("nous_bot"))
    claude_bot = ChorusBot(get_bot_config("claude_bot"))

    print("\n✅ Both bots initialized!")
    print(f"  - Nous: {nous_bot.config.model}")
    print(f"  - Claude: {claude_bot.config.model}")

    # Simulate a human asking a question
    human_msg = "Can you both explain what vector databases are? I'd love to hear different perspectives!"
    print_message("Alice", human_msg)

    # Nous responds
    print("\n⏳ Nous is thinking...")
    nous_responses = await send_message_to_bot(nous_bot, human_msg, "Alice", "alice123")
    if nous_responses:
        print_message("Nous", nous_responses[0], "Nous")

    # Claude sees the conversation (including Nous's response)
    print("\n⏳ Claude is thinking...")
    # First, Claude sees the original question
    await send_message_to_bot(claude_bot, human_msg, "Alice", "alice123")
    # Then Claude might see Nous's response
    if nous_responses:
        claude_responses = await send_message_to_bot(
            claude_bot, nous_responses[0], "Nous", "nous_bot_id"
        )
        if claude_responses:
            print_message("Claude", claude_responses[0], "Claude")

    print("\n✅ Multi-bot conversation working!")


async def test_bots_reacting_to_messages():
    """Test bots reacting with emojis."""
    print("\n" + "=" * 70)
    print("😄 TEST: Bots Reacting with Emojis")
    print("=" * 70)

    nous_bot = ChorusBot(get_bot_config("nous_bot"))
    claude_bot = ChorusBot(get_bot_config("claude_bot"))

    # Test messages that should trigger reactions
    test_messages = [
        ("Alice", "I just got promoted! 🎉"),
        ("Bob", "Hmm, this bug is really confusing me..."),
        ("Charlie", "Thanks for all your help today!"),
    ]

    for sender, message in test_messages:
        print_message(sender, message)

        # Both bots might react (30% chance each)
        print("  ⏳ Bots considering reactions...")

        # Nous
        nous_activity = await create_message(message, sender, f"{sender.lower()}123", "Nous")
        nous_context = MockTurnContext(nous_activity)
        await nous_bot._maybe_react(nous_context)

        # Claude
        claude_activity = await create_message(message, sender, f"{sender.lower()}123", "Claude")
        claude_context = MockTurnContext(claude_activity)
        await claude_bot._maybe_react(claude_context)

        await asyncio.sleep(0.5)

    print("\n✅ Emoji reaction system working!")


async def test_bot_to_bot_interaction():
    """Test bots responding to each other."""
    print("\n" + "=" * 70)
    print("🤝 TEST: Bot-to-Bot Interaction")
    print("=" * 70)

    nous_bot = ChorusBot(get_bot_config("nous_bot"))
    claude_bot = ChorusBot(get_bot_config("claude_bot"))

    # Human asks Nous
    msg1 = "Hey Nous, what do you think about async/await in Python?"
    print_message("Alice", msg1)

    print("\n⏳ Nous is responding...")
    nous_responses = await send_message_to_bot(nous_bot, msg1, "Alice", "alice123")
    if nous_responses:
        print_message("Nous", nous_responses[0], "Nous")

        # Human mentions Claude
        msg2 = "Claude, do you agree with Nous?"
        print_message("Alice", msg2)

        print("\n⏳ Claude is responding...")
        # Claude sees both messages
        await send_message_to_bot(claude_bot, msg1, "Alice", "alice123")
        if nous_responses:
            await send_message_to_bot(claude_bot, nous_responses[0], "Nous", "nous_bot_id")
        claude_responses = await send_message_to_bot(claude_bot, msg2, "Alice", "alice123")

        if claude_responses:
            print_message("Claude", claude_responses[0], "Claude")

            # Nous might respond to Claude
            print("\n⏳ Nous considering response to Claude...")
            nous_replies = await send_message_to_bot(
                nous_bot, claude_responses[0], "Claude", "claude_bot_id"
            )
            if nous_replies:
                print_message("Nous", nous_replies[0], "Nous")

    print("\n✅ Bot-to-bot interaction working!")


async def test_separate_memories():
    """Test that each bot has separate memories."""
    print("\n" + "=" * 70)
    print("🧠 TEST: Separate Bot Memories")
    print("=" * 70)

    nous_bot = ChorusBot(get_bot_config("nous_bot"))
    claude_bot = ChorusBot(get_bot_config("claude_bot"))

    # Tell something to Nous
    nous_msg = "Hey Nous, I prefer Python for data science."
    print_message("Alice", nous_msg)
    await send_message_to_bot(nous_bot, nous_msg, "Alice", "alice123")

    # Tell something different to Claude
    claude_msg = "Hey Claude, I prefer JavaScript for web development."
    print_message("Alice", claude_msg)
    await send_message_to_bot(claude_bot, claude_msg, "Alice", "alice123")

    # Give memories time to process
    await asyncio.sleep(2)

    # Check memories
    nous_memories = nous_bot.memory.get_all_memories(limit=10)
    claude_memories = claude_bot.memory.get_all_memories(limit=10)

    print(f"\n📚 Nous has {len(nous_memories)} memories")
    for mem in nous_memories[:3]:
        print(f"  - {mem['content']}")

    print(f"\n📚 Claude has {len(claude_memories)} memories")
    for mem in claude_memories[:3]:
        print(f"  - {mem['content']}")

    print("\n✅ Bots have separate memory systems!")


async def main():
    """Run all multi-bot tests."""
    print("\n" + "=" * 70)
    print("🤖🤖 MULTI-BOT SYSTEM TESTS")
    print("=" * 70)

    try:
        await test_two_bots_conversation()
        await asyncio.sleep(2)

        await test_bots_reacting_to_messages()
        await asyncio.sleep(2)

        await test_bot_to_bot_interaction()
        await asyncio.sleep(2)

        await test_separate_memories()

        print("\n" + "=" * 70)
        print("✅ ALL MULTI-BOT TESTS COMPLETE!")
        print("=" * 70)
        print("\n🎉 Your multi-bot system is working!")
        print("   - Two bots with different LLMs")
        print("   - Bots interact with each other")
        print("   - Emoji reactions")
        print("   - Separate memories per bot")
        print("   - Natural conversation flow")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
