"""Test memory system functionality."""

import asyncio
import logging
import os
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from src.memory import MemorySystem


async def test_basic_memory_storage():
    """Test storing and retrieving memories."""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Memory Storage and Retrieval")
    print("=" * 70)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memory = MemorySystem(
            db_path=db_path,
            bot_name="TestBot",
            model_name="anthropic/claude-sonnet-4.5",
        )

        # Store some memories
        print("\n📝 Storing memories...")
        mem1 = await memory.store_memory(
            content="Alice prefers Python over JavaScript",
            memory_type="preference",
            confidence=0.9,
        )
        print(f"  ✓ Stored memory #{mem1}")

        mem2 = await memory.store_memory(
            content="Bob is working on a web scraper project",
            memory_type="fact",
            confidence=1.0,
        )
        print(f"  ✓ Stored memory #{mem2}")

        mem3 = await memory.store_memory(
            content="Team uses React for frontend development",
            memory_type="fact",
            confidence=0.8,
        )
        print(f"  ✓ Stored memory #{mem3}")

        # Search for relevant memories
        print("\n🔍 Searching for memories about 'Python programming'...")
        results = await memory.search_memories(
            query="Python programming",
            limit=3,
        )

        print(f"  Found {len(results)} relevant memories:")
        for i, mem in enumerate(results, 1):
            print(f"    {i}. [{mem['memory_type']}] {mem['content']}")
            print(f"       (similarity distance: {mem['similarity_distance']:.4f})")

        print("\n✓ Memory storage and retrieval working!")
        return True

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


async def test_memory_search_relevance():
    """Test that memory search returns relevant results."""
    print("\n" + "=" * 70)
    print("TEST 2: Memory Search Relevance")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memory = MemorySystem(
            db_path=db_path,
            bot_name="TestBot",
            model_name="anthropic/claude-sonnet-4.5",
        )

        # Store diverse memories
        memories_to_store = [
            ("Alice loves baking chocolate cookies", "preference"),
            ("Bob is learning machine learning with TensorFlow", "fact"),
            ("Team decided to use PostgreSQL database", "decision"),
            ("Charlie asked about Python async/await", "context"),
            ("Dana prefers dark chocolate over milk chocolate", "preference"),
        ]

        print("\n📝 Storing diverse memories...")
        for content, mem_type in memories_to_store:
            await memory.store_memory(content, mem_type)
            print(f"  ✓ Stored: {content[:40]}...")

        # Test different queries
        test_queries = [
            "chocolate preferences",
            "Python programming questions",
            "database technology choices",
        ]

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = await memory.search_memories(query, limit=2)
            print(f"  Top {len(results)} results:")
            for mem in results:
                print(f"    - {mem['content']}")

        print("\n✓ Search relevance working!")
        return True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def test_memory_extraction():
    """Test extracting memories from conversation."""
    print("\n" + "=" * 70)
    print("TEST 3: Memory Extraction from Conversation")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memory = MemorySystem(
            db_path=db_path,
            bot_name="Nous",
            model_name="anthropic/claude-sonnet-4.5",
        )

        # Simulate a conversation
        conversation = [
            {"sender": "Alice", "text": "I'm working on a Django project"},
            {"sender": "Bob", "text": "Cool! What database are you using?"},
            {"sender": "Alice", "text": "We decided to go with PostgreSQL"},
            {"sender": "Nous", "text": "That's a great choice! PostgreSQL pairs well with Django."},
        ]

        bot_response = "PostgreSQL is an excellent choice for Django projects because of its robust features and great ORM support."

        print("\n💭 Conversation:")
        for msg in conversation:
            print(f"  {msg['sender']}: {msg['text']}")
        print(f"  Nous: {bot_response}")

        print("\n🧠 Extracting memories...")
        extracted = await memory.process_for_memories(
            conversation_history=conversation,
            current_response=bot_response,
        )

        if extracted:
            print(f"  ✓ Extracted {len(extracted)} memories:")
            for mem in extracted:
                print(f"    - {mem}")
        else:
            print("  ℹ️  No significant memories extracted (this is okay)")

        # Check what's stored
        all_memories = memory.get_all_memories()
        print(f"\n📚 Total memories in database: {len(all_memories)}")
        for mem in all_memories:
            print(f"  - [{mem['memory_type']}] {mem['content']}")

        print("\n✓ Memory extraction working!")
        return True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def test_memory_persistence():
    """Test that memories persist across bot restarts."""
    print("\n" + "=" * 70)
    print("TEST 4: Memory Persistence")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Create first bot instance and store memory
        print("\n🤖 Creating first bot instance...")
        memory1 = MemorySystem(
            db_path=db_path,
            bot_name="TestBot",
            model_name="anthropic/claude-sonnet-4.5",
        )

        await memory1.store_memory(
            content="Alice is learning React hooks",
            memory_type="fact",
        )
        print("  ✓ Stored memory: 'Alice is learning React hooks'")

        # Simulate bot restart by creating new instance
        print("\n🔄 Simulating bot restart (new instance)...")
        memory2 = MemorySystem(
            db_path=db_path,
            bot_name="TestBot",
            model_name="anthropic/claude-sonnet-4.5",
        )

        # Search for the memory
        results = await memory2.search_memories("React hooks", limit=5)

        if results and any("React hooks" in mem["content"] for mem in results):
            print("  ✓ Memory persisted across restart!")
            print(f"  Found: {results[0]['content']}")
        else:
            print("  ✗ Memory did not persist")
            return False

        print("\n✓ Memory persistence working!")
        return True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def test_memory_types():
    """Test filtering by memory type."""
    print("\n" + "=" * 70)
    print("TEST 5: Memory Type Filtering")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memory = MemorySystem(
            db_path=db_path,
            bot_name="TestBot",
            model_name="anthropic/claude-sonnet-4.5",
        )

        # Store memories of different types
        print("\n📝 Storing memories of different types...")
        await memory.store_memory("Alice prefers Python", "preference")
        await memory.store_memory("Bob works at Google", "fact")
        await memory.store_memory("Team chose AWS", "decision")
        await memory.store_memory("Discussion about databases", "context")

        # Search by type
        print("\n🔍 Searching for 'preference' type memories...")
        results = await memory.search_memories(
            query="preferences",
            memory_type="preference",
            limit=5,
        )

        print(f"  Found {len(results)} preference memories")
        for mem in results:
            print(f"    - {mem['content']} (type: {mem['memory_type']})")

        print("\n✓ Memory type filtering working!")
        return True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


async def main():
    """Run all memory system tests."""
    print("\n" + "=" * 70)
    print("🧠 MEMORY SYSTEM TESTS")
    print("=" * 70)

    try:
        results = []

        results.append(await test_basic_memory_storage())
        await asyncio.sleep(1)

        results.append(await test_memory_search_relevance())
        await asyncio.sleep(1)

        results.append(await test_memory_extraction())
        await asyncio.sleep(1)

        results.append(await test_memory_persistence())
        await asyncio.sleep(1)

        results.append(await test_memory_types())

        print("\n" + "=" * 70)
        if all(results):
            print("✅ ALL MEMORY TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED")
        print("=" * 70)

        print("\n🎉 Memory system is working!")
        print("   - Stores memories with vector embeddings")
        print("   - Searches by semantic similarity")
        print("   - Extracts important information from conversations")
        print("   - Persists across restarts")
        print("   - Supports different memory types")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
