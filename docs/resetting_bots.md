# Resetting Bots to Clean Slate

## Quick Reset

To reset a bot's memory and start fresh:

```bash
# Reset a specific bot
rm data/memories/discord_nous.db
rm data/memories/discord_claude.db

# Or use the reset script
uv run python scripts/reset_bot.py discord_nous
uv run python scripts/reset_bot.py discord_claude

# Reset all bots
uv run python scripts/reset_bot.py --all
```

## What Gets Reset

When you delete a bot's memory database:
- ✅ All stored memories (facts, opinions, preferences, etc.)
- ✅ Vector embeddings
- ❌ Conversation history (in-memory only, resets on restart)
- ❌ Bot configuration

## When to Reset

Reset a bot when:
- It's stuck in a loop
- It has incorrect/outdated information in memory
- You want to test fresh behavior
- It's hallucinating about past conversations

## Preventing Loops

**Common causes of loops:**
1. **Display name feedback** - Fixed in discord_bot.py:305
2. **Excessive context** - Reduce `max_messages` in bot config
3. **Memory pollution** - Reset memories periodically
4. **Tool calling issues** - Disable tools if model doesn't support them

**Prevention tips:**
- Set reasonable `max_messages` (20-50 range)
- Enable `max_consecutive_responses` limit (default: 10)
- Monitor for repeated patterns in logs
- Use `ACTIVE_BOTS` to disable problematic bots quickly

## Testing After Reset

1. Delete memory database
2. Restart bot: `ACTIVE_BOTS=nous uv run python discord_app.py`
3. Send test message
4. Check logs for normal behavior

## Emergency Stop

```bash
# Stop all bots immediately
pkill -9 -f "discord_app.py"

# Verify stopped
ps aux | grep discord_app
```
