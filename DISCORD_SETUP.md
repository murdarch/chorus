# Discord Setup Guide

Get your Chorus bots running in Discord in about 15 minutes!

---

## Step 1: Create Discord Applications (5 min)

For each bot you want to run (see `bots/` directory for configured bots):

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Name it: `Chorus <BotName>` (e.g., `Chorus Nous`, `Chorus Claude`)
4. Go to **"Bot"** section in left menu
5. Click **"Add Bot"** → Confirm
6. **IMPORTANT**: Under "Privileged Gateway Intents", enable:
   - ✅ **Message Content Intent** (required!)
   - ✅ **Server Members Intent** (optional)
7. Click **"Reset Token"** → Copy the token
   - **SAVE THIS!** You'll add it to `.env` based on your bot's `discord_token_env` setting

**Example**: If your bot config has `"discord_token_env": "DISCORD_NOUS_TOKEN"`, add the token to `.env` as `DISCORD_NOUS_TOKEN=...`

---

## Step 2: Configure Bots and Update .env (5 min)

### Create Bot Configurations

See [bots/README.md](bots/README.md) for full details. Quick start:

```bash
# Copy the example template for each bot you want
cp -r bots/_example bots/mybot

# Edit config.json to set:
# - model (e.g., "anthropic/claude-sonnet-4.5")
# - discord_token_env (e.g., "DISCORD_MYBOT_TOKEN")
# - capabilities (tools, vision, etc.)

# Edit prompt.txt to customize personality
```

### Add Tokens to .env

Add your Discord tokens to `.env` based on each bot's `discord_token_env` setting:

```bash
# Example tokens (match your bot configs)
DISCORD_NOUS_TOKEN=your_nous_token_here
DISCORD_CLAUDE_TOKEN=your_claude_token_here
DISCORD_MYBOT_TOKEN=your_mybot_token_here
```

---

## Step 3: Invite Bots to Your Server (5 min)

### For Each Bot:

1. In Discord Developer Portal, go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
   - ✅ `bot`
3. Select bot permissions:
   - ✅ `Send Messages`
   - ✅ `Read Messages/View Channels`
   - ✅ `Read Message History`
   - ✅ `Add Reactions`
4. Copy the generated URL at the bottom
5. Open it in a browser
6. Select your Discord server
7. Click **"Authorize"**

Repeat for both bots!

---

## Step 4: Run the Bots (2 min)

```bash
# Run all configured bots
uv run python discord_app.py

# Or run specific bots only
ACTIVE_BOTS=nous,claude uv run python discord_app.py
```

You should see:
```
Starting Chorus Discord bots...
Loaded bot configuration: nous (discord_nous)
Loaded bot configuration: claude (discord_claude)
Loaded 2 bot(s) from bots/ directory
Created bot: Nous (bot_id: discord_nous)
Created bot: Claude (bot_id: discord_claude)
Nous is now online! Connected as Chorus Nous#1234
Claude is now online! Connected as Chorus Claude#5678
```

---

## Step 5: Test in Discord! 🎉

1. Go to your Discord server
2. In any channel where the bots have access:
   - Type: `@Chorus Nous hello!`
   - Type: `@Chorus Claude hello!`
3. Try asking a question: `Can you both explain async/await?`
4. Watch them respond and interact with each other!

### What to expect:

- ✅ Bots respond to direct mentions
- ✅ Bots use intelligent participation (won't spam)
- ✅ Bots react with contextual emojis
- ✅ Bots remember conversations (vector search!)
- ✅ Bots can respond to each other
- ✅ Natural typing indicators

---

## Troubleshooting

### Bot doesn't respond:

1. **Check bot is online**: Look for green status in Discord
2. **Check logs**: Look at terminal output for errors
3. **Check Message Content Intent**: Must be enabled!
4. **Check permissions**: Bot needs "Read Messages" and "Send Messages"

### "401 Unauthorized" error:

- Double-check tokens in `.env`
- Make sure you copied the token, not the Client ID
- Try resetting the token and using the new one

### Bot responds to everything:

- This is by design! The intelligent participation prevents spam
- If it's too chatty, you can adjust the probability in `src/discord_bot.py`

### Rate limiting errors:

- Discord has rate limits (5 messages per 5 seconds)
- The bots respect typing indicators to appear natural
- If hitting limits, consider adding delays

---

## Next Steps

### Running Both Teams and Discord:

You can run both simultaneously!

**Terminal 1 - Teams bots:**
```bash
uv run python app.py
```

**Terminal 2 - Discord bots:**
```bash
uv run python discord_app.py
```

Both sets of bots will have **separate memory systems** (different .db files), so they won't share memories across platforms.

### Sharing Memory Between Platforms:

If you want Teams and Discord bots to share the same memories, use the same `bot_id` in both bot configurations:

```json
// In both bots/discord_nous/config.json and Teams config
{
  "bot_id": "nous_bot",  // Same ID = shared memory database
  ...
}
```

This makes them use the same database file in `data/memories/nous_bot.db`!

---

## Production Deployment

For production:
1. Run on a server (not locally)
2. Use a process manager like `systemd` or `supervisord`
3. Set up logging to files
4. Monitor memory usage
5. Consider rate limiting

---

## Need Help?

- Discord.py docs: https://discordpy.readthedocs.io/
- Issues: https://github.com/murdarch/chorus/issues
