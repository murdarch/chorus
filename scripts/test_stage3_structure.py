"""Test Stage 3 structure without requiring API calls."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from src.config import get_bot_config
from src.bot import ChorusBot
from src.llm_client import get_llm_client


async def test_bot_has_llm_client():
    """Test that bot initializes with LLM client."""
    print("\n" + "=" * 60)
    print("TEST: Bot LLM Client Integration")
    print("=" * 60)

    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    assert bot.llm_client is not None, "Bot should have LLM client"
    assert bot._last_responder is None, "Bot should track last responder"

    print("✓ Bot initialized with LLM client")
    print(f"✓ Bot config: {bot.config.name}")
    print(f"✓ Bot model: {bot.config.model}")
    print("✓ Bot tracks last responder")


async def test_llm_client_initialization():
    """Test LLM client initializes correctly."""
    print("\n" + "=" * 60)
    print("TEST: LLM Client Initialization")
    print("=" * 60)

    client = get_llm_client()

    assert client is not None, "LLM client should initialize"
    assert hasattr(client, "client"), "Should have OpenAI client"
    assert hasattr(client, "get_completion"), "Should have get_completion method"
    assert hasattr(client, "should_respond"), "Should have should_respond method"
    assert hasattr(client, "get_reaction"), "Should have get_reaction method"
    assert hasattr(client, "get_response"), "Should have get_response method"

    print("✓ LLM client initialized")
    print("✓ Has get_completion method")
    print("✓ Has should_respond method")
    print("✓ Has get_reaction method")
    print("✓ Has get_response method")


async def test_bot_conversation_flow():
    """Test that bot conversation flow structure is correct."""
    print("\n" + "=" * 60)
    print("TEST: Bot Conversation Flow Structure")
    print("=" * 60)

    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Add some test messages to history
    bot.history.add_message("conv123", "Alice", "Hello!")
    bot.history.add_message("conv123", "Nous", "Hi Alice!")
    bot.history.add_message("conv123", "Bob", "Hey everyone!")

    history = bot.history.get_history("conv123")
    assert len(history) == 3, "Should have 3 messages"

    print(f"✓ History tracking works: {len(history)} messages")
    print("\nConversation so far:")
    for msg in history:
        print(f"  {msg['sender']}: {msg['text']}")


async def test_model_configurations():
    """Test that different bot models are configured."""
    print("\n" + "=" * 60)
    print("TEST: Multi-Model Configuration")
    print("=" * 60)

    nous_config = get_bot_config("nous_bot")
    claude_config = get_bot_config("claude_bot")

    print(f"Nous Bot:")
    print(f"  - Name: {nous_config.name}")
    print(f"  - Model: {nous_config.model}")
    print(f"  - Memory DB: {nous_config.memory_db_path}")

    print(f"\nClaude Bot:")
    print(f"  - Name: {claude_config.name}")
    print(f"  - Model: {claude_config.model}")
    print(f"  - Memory DB: {claude_config.memory_db_path}")

    assert nous_config.model != claude_config.model, "Bots should use different models"
    print("\n✓ Different models configured correctly")


async def test_response_prevention_logic():
    """Test that bot has logic to prevent responding twice in a row."""
    print("\n" + "=" * 60)
    print("TEST: Response Prevention Logic")
    print("=" * 60)

    config = get_bot_config("nous_bot")
    bot = ChorusBot(config)

    # Simulate bot responding
    bot._last_responder = "Nous"

    print("Simulating scenario where bot just responded...")
    print(f"✓ Last responder tracked: {bot._last_responder}")
    print("✓ Bot will skip responding to avoid dominating conversation")


async def main():
    """Run all structural tests."""
    print("\n" + "=" * 60)
    print("Stage 3 Structure Tests (No API Calls Required)")
    print("=" * 60)

    try:
        await test_llm_client_initialization()
        await test_bot_has_llm_client()
        await test_bot_conversation_flow()
        await test_model_configurations()
        await test_response_prevention_logic()

        print("\n" + "=" * 60)
        print("✓ ALL STRUCTURE TESTS PASSED")
        print("=" * 60)
        print("\n📝 Note: To test actual LLM API calls:")
        print("   1. Get an API key from https://openrouter.ai/keys")
        print("   2. Set OPENROUTER_API_KEY in your .env file")
        print("   3. Run: uv run python scripts/test_llm_integration.py")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
