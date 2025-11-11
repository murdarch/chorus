"""Test LLM integration with OpenRouter.

This script tests the LLM client functionality. It requires a valid OpenRouter API key.
Set OPENROUTER_API_KEY in your .env file to test with real API calls.
"""

import asyncio
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from src.llm_client import LLMClient


async def test_basic_completion():
    """Test basic LLM completion."""
    print("\n" + "=" * 60)
    print("TEST: Basic LLM Completion")
    print("=" * 60)

    client = LLMClient()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, I am working!' in a friendly way."},
    ]

    print("\nSending request to OpenRouter...")
    response = await client.get_completion(
        model="anthropic/claude-3.5-sonnet",
        messages=messages,
        temperature=0.7,
    )

    if response:
        print(f"\n✓ Got response: {response}")
        return True
    else:
        print("\n✗ Failed to get response")
        return False


async def test_should_respond():
    """Test should_respond logic."""
    print("\n" + "=" * 60)
    print("TEST: Should Respond Logic")
    print("=" * 60)

    client = LLMClient()

    # Test case 1: Direct question
    print("\n--- Test Case 1: Direct Question ---")
    history = [
        {"sender": "Alice", "text": "Hello everyone!"},
        {"sender": "Bob", "text": "Hi Alice!"},
    ]
    current_message = "Hey Nous, can you help me with Python?"

    print(f"Current message: {current_message}")
    should_respond = await client.should_respond(
        model="anthropic/claude-3.5-sonnet",
        conversation_history=history,
        bot_name="Nous",
        current_message=current_message,
        sender="Alice",
    )
    print(f"Decision: {'RESPOND' if should_respond else 'SKIP'}")

    # Test case 2: Not relevant
    print("\n--- Test Case 2: Not Relevant ---")
    history = [
        {"sender": "Alice", "text": "What's for lunch?"},
        {"sender": "Bob", "text": "I'm thinking pizza"},
    ]
    current_message = "Sounds good to me!"

    print(f"Current message: {current_message}")
    should_respond = await client.should_respond(
        model="anthropic/claude-3.5-sonnet",
        conversation_history=history,
        bot_name="Nous",
        current_message=current_message,
        sender="Alice",
    )
    print(f"Decision: {'RESPOND' if should_respond else 'SKIP'}")

    return True


async def test_get_reaction():
    """Test emoji reaction selection."""
    print("\n" + "=" * 60)
    print("TEST: Emoji Reaction Selection")
    print("=" * 60)

    client = LLMClient()

    test_cases = [
        ("Alice", "Just finished the project! 🎉"),
        ("Bob", "Hmm, I'm not sure how to solve this..."),
        ("Charlie", "Thanks for your help!"),
    ]

    for sender, message in test_cases:
        print(f"\n{sender}: {message}")
        reaction = await client.get_reaction(
            model="anthropic/claude-3.5-sonnet",
            message=message,
            sender=sender,
            bot_name="Nous",
        )
        if reaction:
            print(f"  → React with: {reaction}")
        else:
            print(f"  → No reaction")

    return True


async def test_conversational_response():
    """Test full conversational response generation."""
    print("\n" + "=" * 60)
    print("TEST: Conversational Response")
    print("=" * 60)

    client = LLMClient()

    system_prompt = """You are Nous, a helpful AI assistant in a Teams chat.
Be friendly, concise, and helpful."""

    history = [
        {"sender": "Alice", "text": "Hey everyone!"},
        {"sender": "Nous", "text": "Hello Alice! How can I help today?"},
        {"sender": "Alice", "text": "I'm learning Python"},
    ]

    current_message = "Can you explain what a list comprehension is?"
    sender = "Alice"

    print(f"\n{sender}: {current_message}")
    print("\nGenerating response...")

    response = await client.get_response(
        model="anthropic/claude-3.5-sonnet",
        system_prompt=system_prompt,
        conversation_history=history,
        current_message=current_message,
        sender=sender,
        bot_name="Nous",
    )

    if response:
        print(f"\nNous: {response}")
        return True
    else:
        print("\n✗ Failed to generate response")
        return False


async def test_different_models():
    """Test with different models."""
    print("\n" + "=" * 60)
    print("TEST: Different Models")
    print("=" * 60)

    client = LLMClient()

    models = [
        "anthropic/claude-3.5-sonnet",
        "nousresearch/hermes-3-llama-3.1-405b",
    ]

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in exactly 5 words."},
    ]

    for model in models:
        print(f"\n--- Testing {model} ---")
        response = await client.get_completion(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=50,
        )
        if response:
            print(f"Response: {response}")
        else:
            print("Failed to get response")

    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LLM Integration Tests")
    print("=" * 60)

    # Check for API key
    from src.config import get_settings
    try:
        settings = get_settings()
        api_key = settings.openrouter_api_key

        if api_key == "test_key_for_stage_2":
            print("\n⚠️  WARNING: Using test API key")
            print("Set a real OPENROUTER_API_KEY in .env to test with actual API")
            print("Get your key at: https://openrouter.ai/keys")
            print("\nSkipping tests that require real API...")
            return
        else:
            print(f"\n✓ Found OpenRouter API key: {api_key[:10]}...")

    except Exception as e:
        print(f"\n✗ Error loading settings: {e}")
        return

    # Run tests
    try:
        results = []

        results.append(await test_basic_completion())
        results.append(await test_should_respond())
        results.append(await test_get_reaction())
        results.append(await test_conversational_response())
        results.append(await test_different_models())

        print("\n" + "=" * 60)
        if all(results):
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
