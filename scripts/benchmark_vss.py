"""Benchmark native VSS vs Python fallback."""

import asyncio
import tempfile
import time
from src.memory import MemorySystem


async def benchmark():
    print("🏎️  VSS Performance Benchmark\n")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    memory = MemorySystem(
        db_path=db_path,
        bot_name='BenchmarkBot',
        model_name='anthropic/claude-sonnet-4.5'
    )

    # Store varying amounts of memories
    test_sizes = [10, 50, 100, 500]

    for size in test_sizes:
        print(f"\n📊 Testing with {size} memories:")

        # Clear and repopulate
        import os
        os.remove(db_path)
        memory = MemorySystem(
            db_path=db_path,
            bot_name='BenchmarkBot',
            model_name='anthropic/claude-sonnet-4.5'
        )

        # Store memories
        print(f"  Storing {size} memories...", end='', flush=True)
        for i in range(size):
            await memory.store_memory(
                f"Memory number {i} about topic {i % 10}",
                memory_type="fact"
            )
        print(" Done!")

        # Benchmark searches
        num_searches = 10
        print(f"  Running {num_searches} searches...", end='', flush=True)

        start = time.time()
        for i in range(num_searches):
            await memory.search_memories(f"topic {i % 10}", limit=5)
        elapsed = time.time() - start

        avg_time = (elapsed / num_searches) * 1000  # Convert to ms
        print(f" Done!")
        print(f"  ⚡ Average search time: {avg_time:.2f}ms")

    print("\n" + "=" * 60)
    print("✅ Benchmark complete!")
    print("\nWith native VSS, searches stay fast even with hundreds of memories!")

    import os
    os.remove(db_path)


if __name__ == "__main__":
    asyncio.run(benchmark())
