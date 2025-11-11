"""Local testing script for bot functionality without Teams."""

import asyncio
import logging
from datetime import datetime
from botbuilder.core import TurnContext
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, ConversationAccount

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Import after logging setup
from src.config import get_bot_config
from src.bot import ChorusBot


async def create_mock_turn_context(text: str, sender_name: str = "Test User") -> TurnContext:
    """Create a mock TurnContext for testing.

    Args:
        text: The message text
        sender_name: Name of the sender

    Returns:
        Mock TurnContext
    """
    # Create activity
    activity = Activity(
        type=ActivityTypes.message,
        text=text,
        from_property=ChannelAccount(id="user123", name=sender_name),
        recipient=ChannelAccount(id="bot456", name="Nous"),
        conversation=ConversationAccount(id="conv789"),
        timestamp=datetime.utcnow(),
    )

    # Create mock turn context
    # Note: We'll need to mock the send_activity method
    class MockTurnContext:
        def __init__(self, activity):
            self.activity = activity
            self.responses = []

        async def send_activity(self, text_or_activity):
            """Mock send_activity to capture responses."""
            if isinstance(text_or_activity, str):
                self.responses.append(text_or_activity)
                print(f"  Bot Response: {text_or_activity}")
            else:
                self.responses.append(text_or_activity.text)
                print(f"  Bot Response: {text_or_activity.text}")

    return MockTurnContext(activity)


async def test_basic_message():
    """Test basic message handling."""
    print("\n" + "=" * 60)
    print("TEST: Basic Message Handling")
    print("=" * 60)

    # Create bot
    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Send a message
    print("\nUser: Hello bot!")
    turn_context = await create_mock_turn_context("Hello bot!")
    await bot.on_message_activity(turn_context)

    # Check response
    assert len(turn_context.responses) == 1
    assert "Echo from Nous" in turn_context.responses[0]
    print("✓ Bot responded correctly")


async def test_conversation_history():
    """Test conversation history tracking."""
    print("\n" + "=" * 60)
    print("TEST: Conversation History")
    print("=" * 60)

    # Create bot
    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Send multiple messages
    messages = [
        "First message",
        "Second message",
        "Third message",
    ]

    for msg in messages:
        print(f"\nUser: {msg}")
        turn_context = await create_mock_turn_context(msg)
        await bot.on_message_activity(turn_context)

    # Check history
    history = bot.history.get_history("conv789")
    # Should have 6 messages (3 from user + 3 from bot)
    assert len(history) == 6, f"Expected 6 messages, got {len(history)}"

    print("\n\nConversation History:")
    print(bot.history.format_history("conv789"))
    print(f"\n✓ History tracking working ({len(history)} messages)")


async def test_ignore_own_messages():
    """Test that bot ignores its own messages."""
    print("\n" + "=" * 60)
    print("TEST: Ignore Own Messages")
    print("=" * 60)

    # Create bot
    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Create activity from bot itself
    activity = Activity(
        type=ActivityTypes.message,
        text="This is from the bot",
        from_property=ChannelAccount(id="bot456", name="Nous"),
        recipient=ChannelAccount(id="bot456", name="Nous"),
        conversation=ConversationAccount(id="conv789"),
    )

    class MockTurnContext:
        def __init__(self, activity):
            self.activity = activity
            self.responses = []

        async def send_activity(self, text_or_activity):
            self.responses.append(text_or_activity)

    turn_context = MockTurnContext(activity)

    print("\nBot (to itself): This is from the bot")
    await bot.on_message_activity(turn_context)

    # Should not respond to own message
    assert len(turn_context.responses) == 0
    print("✓ Bot correctly ignored its own message")


async def test_direct_mention():
    """Test response to direct mentions."""
    print("\n" + "=" * 60)
    print("TEST: Direct Mention Detection")
    print("=" * 60)

    # Create bot
    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Send message with bot name
    print("\nUser: Hey Nous, can you help me?")
    turn_context = await create_mock_turn_context("Hey Nous, can you help me?")
    await bot.on_message_activity(turn_context)

    # Should respond
    assert len(turn_context.responses) == 1
    print("✓ Bot responded to mention of its name")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Chorus Bot - Local Testing")
    print("=" * 60)

    try:
        await test_basic_message()
        await test_conversation_history()
        await test_ignore_own_messages()
        await test_direct_mention()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
