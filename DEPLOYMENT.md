# Deploying Chorus to Microsoft Teams

This guide will walk you through deploying your Chorus bots to Microsoft Teams.

## Prerequisites

- [ ] Microsoft 365 account with Teams
- [ ] Azure subscription (free tier works)
- [ ] OpenRouter API key (already have this!)
- [ ] Public endpoint for your bot (ngrok or deployed server)

---

## Step 1: Create Azure Bot Registrations

You need to create **two separate** Bot Channel Registrations in Azure (one for each bot).

### For Nous Bot:

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource** → Search for "Azure Bot"
3. Click **Azure Bot** → **Create**
4. Fill in the details:
   - **Bot handle**: `chorus-nous-bot` (must be globally unique)
   - **Subscription**: Your Azure subscription
   - **Resource group**: Create new → `chorus-bots-rg`
   - **Pricing tier**: F0 (Free)
   - **Microsoft App ID**: Create new Microsoft App ID
5. Click **Review + Create** → **Create**
6. Once created, go to the bot resource → **Configuration**
7. Set **Messaging endpoint**: `https://your-domain.ngrok.io/api/messages/nous_bot`
8. Go to **Settings** → **Manage** (next to Microsoft App ID)
9. Click **New client secret** → Create a secret
10. **SAVE THESE VALUES**:
    - Application (client) ID → This is your `NOUS_BOT_APP_ID`
    - Client secret value → This is your `NOUS_BOT_APP_PASSWORD`

### For Claude Bot:

Repeat the exact same steps but use:
- **Bot handle**: `chorus-claude-bot`
- **Messaging endpoint**: `https://your-domain.ngrok.io/api/messages/claude_bot`
- Save the App ID → `CLAUDE_BOT_APP_ID`
- Save the secret → `CLAUDE_BOT_APP_PASSWORD`

### Add Microsoft Teams Channel

For **both bots**:
1. Go to the bot resource in Azure Portal
2. Click **Channels** → Click **Microsoft Teams** icon
3. Click **Save**
4. Click **Agree** to the terms

---

## Step 2: Update Your .env File

Update your `.env` file with the Azure credentials:

```bash
# OpenRouter API (you already have this)
OPENROUTER_API_KEY=your_openrouter_key

# Azure Bot Service - Nous Bot
NOUS_BOT_APP_ID=<your-nous-app-id-from-azure>
NOUS_BOT_APP_PASSWORD=<your-nous-secret-from-azure>

# Azure Bot Service - Claude Bot
CLAUDE_BOT_APP_ID=<your-claude-app-id-from-azure>
CLAUDE_BOT_APP_PASSWORD=<your-claude-secret-from-azure>

# Server Configuration
PORT=3978
HOST=0.0.0.0
LOG_LEVEL=INFO
```

---

## Step 3: Expose Your Bot to the Internet

You have two options:

### Option A: Use ngrok (Quick Local Testing)

1. Install ngrok: https://ngrok.com/download
2. Start your bot:
   ```bash
   uv run python app.py
   ```
3. In another terminal, expose port 3978:
   ```bash
   ngrok http 3978
   ```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Update the **Messaging endpoint** in Azure for both bots:
   - Nous: `https://abc123.ngrok.io/api/messages/nous_bot`
   - Claude: `https://abc123.ngrok.io/api/messages/claude_bot`

**Note**: ngrok URLs change when you restart. For production, use Option B.

### Option B: Deploy to a Server (Production)

Deploy to Azure App Service, AWS, DigitalOcean, or any server with:
- Python 3.11+
- Public IP/domain
- SSL certificate (Let's Encrypt)
- systemd service or similar for auto-restart

Example for Ubuntu server:
```bash
# Install dependencies
sudo apt-get install libblas3 liblapack3

# Clone repo and setup
cd /opt
git clone <your-repo>
cd chorus
uv sync

# Create systemd service
sudo nano /etc/systemd/system/chorus.service
```

Service file:
```ini
[Unit]
Description=Chorus Multi-Bot System
After=network.target

[Service]
Type=simple
User=chorus
WorkingDirectory=/opt/chorus
Environment="PATH=/opt/chorus/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/chorus/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Step 4: Create Teams App Manifest

Create the Teams app package with both bots.

### Create Icon Files

Create two icon files in `teams-app/icons/`:
- `color-icon.png` (192x192 px, colored version)
- `outline-icon.png` (32x32 px, transparent outline)

You can use simple placeholder icons or create custom ones.

### Create Manifest

The manifest is already created at `teams-app/manifest.json`. Update it with your bot IDs:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "<generate-new-guid>",
  "packageName": "com.yourcompany.chorus",
  "developer": {
    "name": "Your Company",
    "websiteUrl": "https://yourcompany.com",
    "privacyUrl": "https://yourcompany.com/privacy",
    "termsOfUseUrl": "https://yourcompany.com/terms"
  },
  "name": {
    "short": "Chorus Bots",
    "full": "Chorus Multi-LLM Chat Bots"
  },
  "description": {
    "short": "AI bots that chat together",
    "full": "Multiple LLM-powered bots that participate naturally in Teams conversations"
  },
  "icons": {
    "outline": "icons/outline-icon.png",
    "color": "icons/color-icon.png"
  },
  "accentColor": "#5558AF",
  "bots": [
    {
      "botId": "<YOUR-NOUS-BOT-APP-ID>",
      "scopes": ["personal", "team", "groupchat"],
      "supportsFiles": false,
      "isNotificationOnly": false
    },
    {
      "botId": "<YOUR-CLAUDE-BOT-APP-ID>",
      "scopes": ["personal", "team", "groupchat"],
      "supportsFiles": false,
      "isNotificationOnly": false
    }
  ],
  "permissions": [
    "identity",
    "messageTeamMembers"
  ],
  "validDomains": []
}
```

### Generate a New GUID

```bash
uv run python -c "import uuid; print(uuid.uuid4())"
```

Use this as the manifest `id`.

### Package the App

```bash
cd teams-app
zip -r chorus-app.zip manifest.json icons/
```

---

## Step 5: Upload to Teams

1. Open Microsoft Teams
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select your `chorus-app.zip` file
6. Click **Add** (or **Add to a team/chat**)

---

## Step 6: Test Your Bots!

### In a Team Channel:

1. Add both bots to a channel
2. Type: `@Nous Hello!`
3. Type: `@Claude Hello!`
4. Ask a question: "Can you both explain what async/await is?"
5. Watch them interact! 🎉

### In a Group Chat:

1. Create a new chat
2. Add both bots as participants
3. Start chatting!

---

## Troubleshooting

### Bot doesn't respond:

1. Check bot is running: `curl http://localhost:3978/health`
2. Check ngrok is forwarding: Visit your ngrok URL in browser
3. Check Azure messaging endpoint is correct
4. Check logs: `uv run python app.py` and watch for errors
5. Test with Bot Framework Emulator

### "Unauthorized" errors:

- Double-check `NOUS_BOT_APP_ID` and `NOUS_BOT_APP_PASSWORD` in `.env`
- Make sure you copied the **secret value**, not the secret ID
- Secret expires after 24 months - create new one if expired

### Bots see messages but don't respond:

- Check OpenRouter API key is valid
- Check logs for LLM errors
- Try mentioning bot directly: `@Nous hello`

### ngrok session expired:

- Free ngrok URLs expire after 2 hours
- Restart ngrok, get new URL
- Update messaging endpoints in Azure Portal

---

## Production Checklist

Before going live:

- [ ] Deploy to permanent server (not ngrok)
- [ ] Set up SSL certificate
- [ ] Configure systemd service for auto-restart
- [ ] Set up log rotation
- [ ] Monitor API costs (OpenRouter)
- [ ] Set up error alerting
- [ ] Backup memory databases regularly
- [ ] Test failover scenarios
- [ ] Document team onboarding process

---

## Cost Estimates

### Azure Bot Service:
- **F0 Tier**: FREE (10,000 messages/month)
- **S1 Tier**: $0.50 per 1000 messages

### OpenRouter API:
- **Hermes 4 (405B)**: ~$5-15 per 1M tokens
- **Claude Sonnet 4.5**: ~$3-15 per 1M tokens
- Typical conversation: 500-2000 tokens
- **Estimate**: $10-50/month for moderate usage

### Server (if not using local):
- **DigitalOcean Droplet**: $6-12/month
- **Azure App Service**: $13-55/month
- **AWS EC2**: $8-30/month

---

## Next Steps

1. **Create Azure bots** (15 minutes)
2. **Start ngrok** (2 minutes)
3. **Create Teams manifest** (5 minutes)
4. **Upload to Teams** (2 minutes)
5. **Start chatting!** (infinite fun 🎉)

Good luck! Your bots are about to come alive! 🤖💬🤖
