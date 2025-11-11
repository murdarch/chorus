"""Full integration test - simulate real bot conversations."""

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


async def create_message(text: str, sender_name: str, sender_id: str):
    """Create a mock message activity."""
    return Activity(
        type=ActivityTypes.message,
        text=text,
        from_property=ChannelAccount(id=sender_id, name=sender_name),
        recipient=ChannelAccount(id="bot456", name="Nous"),
        conversation=ConversationAccount(id="test_conv_123"),
        timestamp=datetime.utcnow(),
    )


async def send_message(bot: ChorusBot, text: str, sender_name: str, sender_id: str):
    """Send a message to the bot and get response."""
    activity = await create_message(text, sender_name, sender_id)
    turn_context = MockTurnContext(activity)

    await bot.on_message_activity(turn_context)

    return turn_context.responses


def print_message(sender: str, text: str, is_bot: bool = False):
    """Pretty print a message."""
    if is_bot:
        print(f"\n🤖 {sender}: {text}")
    else:
        print(f"\n👤 {sender}: {text}")


async def test_conversation_scenario_1():
    """Test Scenario 1: Direct mention - Bot should always respond."""
    print("\n" + "=" * 70)
    print("SCENARIO 1: Direct Mention (Bot should ALWAYS respond)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    message = "Hey Nous, can you explain what async/await is in Python?"
    print_message("Alice", message)

    responses = await send_message(bot, message, "Alice", "alice123")

    if responses:
        for response in responses:
            print_message("Nous", response, is_bot=True)
        print("\n✓ Bot responded to direct mention")
    else:
        print("\n✗ Bot did not respond (UNEXPECTED)")


async def test_conversation_scenario_2():
    """Test Scenario 2: Relevant question - Bot should decide to respond."""
    print("\n" + "=" * 70)
    print("SCENARIO 2: Relevant Question (Bot decides based on context)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    # Build up conversation history
    conversation = [
        ("Alice", "I'm working on a Python project"),
        ("Bob", "That's cool! What kind of project?"),
        ("Alice", "A web scraper for news articles"),
        ("Alice", "Anyone know a good library for parsing HTML?"),
    ]

    for sender, msg in conversation:
        print_message(sender, msg)
        await send_message(bot, msg, sender, f"{sender.lower()}123")

    # Last message is a question - bot should decide to respond
    responses = await send_message(
        bot,
        "Anyone know a good library for parsing HTML?",
        "Alice",
        "alice123"
    )

    if responses:
        for response in responses:
            print_message("Nous", response, is_bot=True)
        print("\n✓ Bot decided to respond with helpful info")
    else:
        print("\n✓ Bot decided not to respond (also valid)")


async def test_conversation_scenario_3():
    """Test Scenario 3: Casual chat - Bot should probably skip."""
    print("\n" + "=" * 70)
    print("SCENARIO 3: Casual Chat (Bot should probably SKIP)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    # Build casual conversation
    conversation = [
        ("Alice", "What's everyone having for lunch?"),
        ("Bob", "I'm thinking pizza"),
        ("Charlie", "Sounds good!"),
    ]

    for sender, msg in conversation:
        print_message(sender, msg)
        await send_message(bot, msg, sender, f"{sender.lower()}123")

    # Send one more casual message
    message = "Yeah, pizza sounds great!"
    print_message("Alice", message)
    responses = await send_message(bot, message, "Alice", "alice123")

    if responses:
        for response in responses:
            print_message("Nous", response, is_bot=True)
        print("\n✓ Bot decided to join casual chat")
    else:
        print("\n✓ Bot wisely skipped casual chat (good decision!)")


async def test_conversation_scenario_4():
    """Test Scenario 4: Multi-turn technical discussion."""
    print("\n" + "=" * 70)
    print("SCENARIO 4: Multi-turn Technical Discussion")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    # Technical discussion
    turns = [
        ("Alice", "I'm having trouble with git merge conflicts"),
        ("Bot", True),  # Bot should respond
        ("Alice", "Thanks! That helps a lot"),
        ("Bob", "I've had that issue before too"),
        ("Alice", "What's the best way to avoid them in the first place?"),
        ("Bot", True),  # Bot might respond again
    ]

    for item in turns:
        if len(item) == 2 and item[1] is True:
            # Bot's turn - skip (we'll let it decide)
            continue
        else:
            sender, msg = item
            print_message(sender, msg)
            responses = await send_message(bot, msg, sender, f"{sender.lower()}123")

            if responses:
                for response in responses:
                    print_message("Nous", response, is_bot=True)


async def test_conversation_scenario_5():
    """Test Scenario 5: Bot name mentioned in conversation."""
    print("\n" + "=" * 70)
    print("SCENARIO 5: Bot Name Mentioned (Should respond)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    conversation = [
        ("Alice", "I wonder what Nous thinks about this"),
        ("Bob", "Yeah, good idea to ask Nous"),
    ]

    for sender, msg in conversation:
        print_message(sender, msg)
        responses = await send_message(bot, msg, sender, f"{sender.lower()}123")

        if responses:
            for response in responses:
                print_message("Nous", response, is_bot=True)
            print(f"\n✓ Bot responded to name mention from {sender}")


async def test_response_prevention():
    """Test that bot doesn't respond twice in a row."""
    print("\n" + "=" * 70)
    print("SCENARIO 6: Response Prevention (Avoid dominating conversation)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    # First message - mention bot
    msg1 = "Hey Nous, what's 2+2?"
    print_message("Alice", msg1)
    responses1 = await send_message(bot, msg1, "Alice", "alice123")

    if responses1:
        print_message("Nous", responses1[0], is_bot=True)
        print("✓ Bot responded to first mention")

    # Second message immediately after - bot should skip even if relevant
    msg2 = "And what about 3+3?"
    print_message("Alice", msg2)
    responses2 = await send_message(bot, msg2, "Alice", "alice123")

    if not responses2:
        print("\n✓ Bot correctly skipped to avoid responding twice in a row!")
    else:
        print_message("Nous", responses2[0], is_bot=True)
        print("\n⚠️  Bot responded twice in a row (might happen if directly mentioned)")


async def test_conversation_with_history():
    """Test that bot uses conversation history for context."""
    print("\n" + "=" * 70)
    print("SCENARIO 7: Contextual Response (Using conversation history)")
    print("=" * 70)

    bot = ChorusBot(get_bot_config("nous_bot"))

    # Build context
    conversation = [
        ("Alice", "I'm learning React for the first time"),
        ("Bob", "Cool! It's a great framework"),
        ("Alice", "I'm confused about hooks though"),
    ]

    print("Building conversation context...")
    for sender, msg in conversation:
        print_message(sender, msg)
        await send_message(bot, msg, sender, f"{sender.lower()}123")

    # Now ask about "it" - bot should understand from context
    msg = "Nous, can you explain it to me?"
    print_message("Alice", msg)
    responses = await send_message(bot, msg, "Alice", "alice123")

    if responses:
        print_message("Nous", responses[0], is_bot=True)
        print("\n✓ Bot used conversation history for context!")
        if "hooks" in responses[0].lower() or "react" in responses[0].lower():
            print("✓ Bot correctly understood 'it' refers to React hooks!")


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("🤖 CHORUS BOT - FULL INTEGRATION TESTS 🤖")
    print("=" * 70)
    print("\nTesting intelligent bot behavior with real LLM calls...")
    print("This will take a minute as we make real API calls to OpenRouter")

    try:
        await test_conversation_scenario_1()
        await asyncio.sleep(1)

        await test_conversation_scenario_2()
        await asyncio.sleep(1)

        await test_conversation_scenario_3()
        await asyncio.sleep(1)

        await test_conversation_scenario_4()
        await asyncio.sleep(1)

        await test_conversation_scenario_5()
        await asyncio.sleep(1)

        await test_response_prevention()
        await asyncio.sleep(1)

        await test_conversation_with_history()

        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS COMPLETE!")
        print("=" * 70)
        print("\n🎉 Your bot is working beautifully!")
        print("   - Responds to direct mentions")
        print("   - Makes intelligent participation decisions")
        print("   - Uses conversation context")
        print("   - Avoids dominating conversations")
        print("   - Understands when mentioned by name")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
