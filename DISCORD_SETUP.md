# Discord Setup Guide

Get your Chorus bots running in Discord in about 15 minutes!

---

## Step 1: Create Discord Applications (5 min)

### Create Nous Bot:

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Name it: `Chorus Nous`
4. Go to **"Bot"** section in left menu
5. Click **"Add Bot"** → Confirm
6. **IMPORTANT**: Under "Privileged Gateway Intents", enable:
   - ✅ **Message Content Intent** (required!)
   - ✅ **Server Members Intent** (optional)
7. Click **"Reset Token"** → Copy the token
   - **SAVE THIS!** You'll add it to `.env` as `DISCORD_NOUS_TOKEN`

### Create Claude Bot:

Repeat the same steps above but name it `Chorus Claude`
- Save the token as `DISCORD_CLAUDE_TOKEN`

---

## Step 2: Update .env File (1 min)

Add your Discord tokens to `.env`:

```bash
# Add these lines to your existing .env file
DISCORD_NOUS_TOKEN=your_nous_token_here
DISCORD_CLAUDE_TOKEN=your_claude_token_here
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
cd /home/murdarch/src/python/chorus
uv run python discord_app.py
```

You should see:
```
Starting Chorus Discord bots...
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

If you want Teams and Discord bots to share the same memories, modify the `bot_id` in `get_discord_bot_configs()` in `src/config.py`:

```python
# Change from:
bot_id="discord_nous",

# To:
bot_id="nous_bot",  # Same as Teams bot
```

This makes them use the same database file!

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
