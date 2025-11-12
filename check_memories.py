#!/usr/bin/env python
"""Check memories stored in the bot databases."""

import sqlite3
from pathlib import Path

def check_memories(db_path: str, bot_name: str):
    """Check and display memories from a database."""
    if not Path(db_path).exists():
        print(f"{bot_name}: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM memories")
    total = cursor.fetchone()[0]
    print(f"\n{bot_name} - Total memories: {total}")

    if total > 0:
        # Get last 10 memories
        cursor.execute("""
            SELECT id, memory_type, content, timestamp
            FROM memories
            ORDER BY timestamp DESC
            LIMIT 10
        """)

        print(f"\nLast 10 memories:")
        for row in cursor.fetchall():
            memory_id, mem_type, content, timestamp = row
            # Truncate long content
            display_content = content[:100] + "..." if len(content) > 100 else content
            print(f"  #{memory_id} [{mem_type}] {display_content}")
            print(f"    Created: {timestamp}")

    conn.close()

if __name__ == "__main__":
    print("=" * 80)
    print("CHORUS BOT MEMORY DATABASE REPORT")
    print("=" * 80)

    # Check Discord bots
    check_memories("data/memories/discord_nous.db", "Discord Nous")
    check_memories("data/memories/discord_claude.db", "Discord Claude")

    # Check Teams bots
    check_memories("data/memories/nous_bot.db", "Teams Nous")
    check_memories("data/memories/claude_bot.db", "Teams Claude")

    print("\n" + "=" * 80)
