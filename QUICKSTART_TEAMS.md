# Quick Start: Deploy to Teams (5 Steps)

Get your Chorus bots running in Teams in about 30 minutes!

---

## Step 1: Install ngrok (5 min)

Download and install ngrok to expose your local server:

```bash
# Visit https://ngrok.com/download or:
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

Sign up for free account: https://dashboard.ngrok.com/signup

Get your authtoken:
```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

---

## Step 2: Start Your Bot & Expose It (2 min)

Terminal 1 - Start bot:
```bash
cd /home/murdarch/src/python/chorus
uv run python app.py
```

Terminal 2 - Start ngrok:
```bash
ngrok http 3978
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

**IMPORTANT**: Save this URL! You'll need it for Azure.

---

## Step 3: Create Azure Bot Registrations (10 min)

### Create Nous Bot:

1. Go to https://portal.azure.com
2. Search "Azure Bot" → Create
3. Settings:
   - **Bot handle**: `chorus-nous-yourname` (must be unique)
   - **Pricing**: F0 (Free)
   - **Microsoft App ID**: Create new
4. After creation → Configuration → Set:
   - **Messaging endpoint**: `https://YOUR-NGROK-URL/api/messages/nous_bot`
5. Go to Settings → Manage (by App ID) → New client secret
6. **COPY THESE**:
   - **Application ID**
   - **Secret Value** (NOT Secret ID!)
7. Go to Channels → Add Microsoft Teams channel

### Create Claude Bot:

Repeat above steps with:
- **Bot handle**: `chorus-claude-yourname`
- **Messaging endpoint**: `https://YOUR-NGROK-URL/api/messages/claude_bot`
- Copy its App ID and Secret too

---

## Step 4: Update .env File (1 min)

Edit your `.env` file:

```bash
OPENROUTER_API_KEY=your_key_here

# From Azure Nous Bot:
NOUS_BOT_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOUS_BOT_APP_PASSWORD=your_secret_here

# From Azure Claude Bot:
CLAUDE_BOT_APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLAUDE_BOT_APP_PASSWORD=your_secret_here

PORT=3978
LOG_LEVEL=INFO
```

**Restart your bot** after updating .env!

---

## Step 5: Create & Upload Teams App (5 min)

### Prepare the package:

```bash
uv run python scripts/prepare_teams_package.py
```

This will:
- Update manifest.json with your bot IDs
- Create chorus-app.zip package

### Upload to Teams:

1. Open **Microsoft Teams**
2. Click **Apps** (left sidebar)
3. Click **Manage your apps** (bottom)
4. Click **Upload an app** → **Upload a custom app**
5. Select `teams-app/chorus-app.zip`
6. Click **Add**
7. Add to a team or chat

---

## Step 6: Test! 🎉

In Teams:

1. **Add both bots** to a channel or chat
2. Type: `@Nous Hello!`
3. Type: `@Claude Hello!`
4. Ask a question: "Can you both explain async/await?"
5. Watch them interact! 🤖💬🤖

---

## Troubleshooting

### Bot doesn't respond:

```bash
# Check bot is running
curl http://localhost:3978/health

# Check ngrok is working
curl https://YOUR-NGROK-URL/health

# Check logs
uv run python app.py
# Look for errors
```

### "Unauthorized" error:

- Double-check App IDs and Secrets in .env
- Make sure you copied the **Secret Value**, not Secret ID
- Restart bot after changing .env

### Wrong ngrok URL:

1. Stop bot (Ctrl+C)
2. Stop ngrok (Ctrl+C)
3. Restart ngrok → Get new URL
4. Update Azure messaging endpoints
5. Restart bot

---

## What's Next?

Your bots are now live! They can:
- ✅ Respond to mentions
- ✅ Have conversations with each other
- ✅ React with emojis 😄
- ✅ Remember conversations 🧠
- ✅ Make intelligent decisions 🎯

### For Production:

- Deploy to a permanent server (see DEPLOYMENT.md)
- Set up monitoring
- Configure backups
- Add more bots!

---

## Need Help?

Check the full deployment guide: `DEPLOYMENT.md`

Or visit: https://github.com/anthropics/claude-code/issues
