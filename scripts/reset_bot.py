#!/usr/bin/env python3
"""Reset a bot to clean slate by clearing its memory and conversation history."""

import argparse
import os
import sys
from pathlib import Path

def reset_bot(bot_id: str):
    """Reset a bot by clearing its memory database.

    Args:
        bot_id: Bot ID (e.g., 'discord_nous', 'discord_claude')
    """
    # Path to memory database
    db_path = Path(f"data/memories/{bot_id}.db")

    if not db_path.exists():
        print(f"❌ No memory database found for bot '{bot_id}'")
        print(f"   Expected: {db_path}")
        return False

    # Delete the database
    try:
        db_path.unlink()
        print(f"✅ Deleted memory database: {db_path}")
        print(f"✅ Bot '{bot_id}' reset to clean slate")
        print("\nNote: Conversation history (in-memory) will reset when bot restarts")
        return True
    except Exception as e:
        print(f"❌ Error deleting database: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Reset a bot to clean slate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset Nous bot
  python scripts/reset_bot.py discord_nous

  # Reset Claude bot
  python scripts/reset_bot.py discord_claude

  # Reset all bots
  python scripts/reset_bot.py --all
        """
    )
    parser.add_argument(
        "bot_id",
        nargs="?",
        help="Bot ID to reset (e.g., discord_nous, discord_claude)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all bots"
    )

    args = parser.parse_args()

    if args.all:
        # Find all memory databases
        memory_dir = Path("data/memories")
        if not memory_dir.exists():
            print("❌ No memories directory found")
            return 1

        db_files = list(memory_dir.glob("*.db"))
        if not db_files:
            print("ℹ️  No bot databases found")
            return 0

        print(f"Found {len(db_files)} bot database(s)")
        confirm = input("Are you sure you want to reset ALL bots? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled")
            return 0

        for db_file in db_files:
            bot_id = db_file.stem
            print(f"\nResetting {bot_id}...")
            reset_bot(bot_id)

        print("\n✅ All bots reset!")
        return 0

    if not args.bot_id:
        parser.print_help()
        return 1

    return 0 if reset_bot(args.bot_id) else 1


if __name__ == "__main__":
    sys.exit(main())
