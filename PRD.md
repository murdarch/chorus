# Product Requirements Document: Multi-LLM Teams Chat Bot System

## Project Overview
Build a Microsoft Teams integration that allows multiple LLM-powered bots (via OpenRouter) to participate as natural members in Teams conversations. Each bot can interact with humans and other bots through messages and emoji reactions.

## Core MVP Requirements

### 1. Bot Participants
- Implement 2 distinct bots minimum with different LLM backends via OpenRouter
- Each bot appears as a separate participant in Teams with unique name/avatar
- Bots can see and respond to messages from both humans and other bots
- Natural conversation flow - bots should not always respond to every message

### 2. OpenRouter Integration
- All LLMs accessed through OpenRouter's unified API
- Use OpenAI-compatible client library pointing to OpenRouter endpoint
- Configurable model selection per bot
- Example configuration:
  - Bot 1: Nous Hermes 4 (`nousresearch/hermes-4-405b`)
  - Bot 2: Claude Sonnet 4.5 (`anthropic/claude-sonnet-4.5`)

### 3. Interaction Features
- **Text Messages**: Bots can send conversational responses
- **Emoji Reactions**: Bots can add reactions (❤️ 👍 😄 🎉 🤔 👀 🚀 💡 ✅) to any message
- **Smart Participation**: Bots use LLM to decide when to respond/react based on context
- **Bot-to-Bot Interaction**: Bots can respond to and react to each other's messages

### 4. Memory System
- Use SQLite with sqlite-vss extension for vector similarity search
- Each bot maintains independent memory storage
- Memories persist across conversation sessions
- Vector embeddings using sentence-transformers (all-MiniLM-L6-v2)
- Memory types: facts, impressions, decisions, context

## Technical Implementation

### Technology Stack
- **Language**: Python 3.11+
- **Package Manager**: uv
- **Bot Framework**: botbuilder-core (Microsoft Bot Framework SDK)
- **LLM API**: OpenRouter (via OpenAI client library)
- **Memory Storage**: SQLite with sqlite-vss
- **Embeddings**: sentence-transformers
- **Web Framework**: aiohttp
- **Environment**: python-dotenv for configuration

### Project Structure
```
chorus/
├── pyproject.toml          # uv project configuration
├── .env                    # API keys and configuration
├── .env.example           # Template for environment variables
├── app.py                 # Main application entry point
├── src/
│   ├── __init__.py
│   ├── bot.py            # Main bot class with message handling
│   ├── memory.py         # SQLite-vss memory system
│   ├── llm_client.py     # OpenRouter integration
│   ├── reactions.py      # Reaction decision logic
│   └── config.py         # Configuration and bot profiles
├── data/
│   └── memories/         # SQLite database files for each bot
├── scripts/
│   ├── setup_azure.py    # Helper script for Azure bot registration
│   └── test_bot.py       # Local testing script
├── teams-app/
│   ├── manifest.json     # Teams app manifest
│   └── icons/           # Bot icons for Teams
└── README.md            # Setup and deployment instructions
```

## Detailed Implementation Specifications

### 1. Configuration System (`src/config.py`)

```python
# Environment variables needed:
OPENROUTER_API_KEY=<openrouter-api-key>

# Azure Bot Service credentials for each bot
NOUS_BOT_APP_ID=<azure-app-id-1>
NOUS_BOT_APP_PASSWORD=<azure-password-1>
CLAUDE_BOT_APP_ID=<azure-app-id-2>  
CLAUDE_BOT_APP_PASSWORD=<azure-password-2>

# Server configuration
PORT=3978  # Default port for Bot Framework

# Bot configurations dictionary
BOT_CONFIGS = {
    "nous_bot": {
        "app_id": NOUS_BOT_APP_ID,
        "app_password": NOUS_BOT_APP_PASSWORD,
        "name": "Nous",
        "model": "nousresearch/hermes-4-405b",
        "system_prompt": "You are participating in a Teams chat as Nous, an AI assistant."
    },
    "claude_bot": {
        "app_id": CLAUDE_BOT_APP_ID,
        "app_password": CLAUDE_BOT_APP_PASSWORD,
        "name": "Claude",
        "model": "anthropic/claude-sonnet-4.5",
        "system_prompt": "You are participating in a Teams chat as Claude, an AI assistant."
    }
}
```

### 2. LLM Client (`src/llm_client.py`)

Implement OpenRouter client with these methods:
- `get_completion(model, messages, temperature)`: Get LLM response
- `should_respond(model, conversation, bot_name)`: Let LLM decide if bot should respond
- `get_reaction(model, message, sender, bot_name)`: Get emoji reaction or 'none'

Key details:
- Base URL: `https://openrouter.ai/api/v1`
- Use AsyncOpenAI client for compatibility
- Include conversation history in prompts for context
- Temperature: 0.7 for responses, 0.3 for decisions, 0.5 for reactions

### 3. Memory System (`src/memory.py`)

SQLite database schema:
```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    memory_type TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence REAL,
    embedding BLOB,
    metadata TEXT  -- JSON
);

CREATE VIRTUAL TABLE vss_memories USING vss0(
    embedding(384)  -- Dimension for all-MiniLM-L6-v2
);
```

Core methods:
- `store_memory(content)`: Store with generated embedding
- `search_memories(query, limit=5)`: Vector similarity search
- `process_for_memories(conversation)`: Extract important info from chat

### 4. Main Bot Class (`src/bot.py`)

Bot behavior logic:
1. **Message Handling**:
   - Track conversation history per conversation ID
   - Don't respond to own messages
   - Check if bot should respond using:
     - Direct mentions (always respond)
     - Recent activity (avoid responding twice in a row)
     - LLM decision based on context

2. **Response Generation**:
   - Retrieve relevant memories (top 3)
   - Include memories in system prompt
   - Use last 10 messages for context
   - Store important information after responding

3. **Reaction Logic**:
   - 30% chance to consider reacting
   - Use LLM to choose appropriate emoji
   - Add 1-3 second natural delay
   - Can react to both human and bot messages

### 5. Application Server (`app.py`)

Web server setup:
- Separate endpoint for each bot: `/api/messages/{bot_name}`
- Bot Framework adapter for each bot configuration
- Route messages to appropriate bot based on URL
- Handle both message activities and reaction activities

### 6. Deployment Configuration

#### pyproject.toml
```toml
[project]
name = "chorus"
version = "0.1.0"
description = "Multi-LLM Teams chat bots"
requires-python = ">=3.11"
dependencies = [
    "botbuilder-core>=4.14.0",
    "aiohttp>=3.9.0",
    "openai>=1.0.0",
    "sqlite-vss>=0.1.2",
    "numpy>=1.24.0",
    "sentence-transformers>=2.2.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]
```

#### Teams App Manifest
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "<unique-app-id>",
  "packageName": "com.yourcompany.multillm",
  "name": {
    "short": "Multi-LLM Bots",
    "full": "Multiple LLM Chat Participants"
  },
  "description": {
    "short": "LLM bots that participate in chat",
    "full": "Multiple LLM-powered bots that participate naturally in Teams conversations"
  },
  "bots": [
    {
      "botId": "<nous-bot-app-id>",
      "scopes": ["personal", "team", "groupchat"],
      "supportsFiles": false
    },
    {
      "botId": "<claude-bot-app-id>",
      "scopes": ["personal", "team", "groupchat"],
      "supportsFiles": false
    }
  ],
  "permissions": ["identity", "messageTeamMembers"],
  "validDomains": ["<your-domain>"]
}
```

## Setup Instructions

### 1. Azure Setup
1. Create two Bot Channels Registration resources in Azure Portal
2. For each bot:
   - Note the Microsoft App ID
   - Create new client secret (password)
   - Set Messaging endpoint to `https://your-domain/api/messages/{bot_name}`

### 2. Local Development
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project directory
mkdir chorus
cd chorus

# Initialize project with uv
uv init
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Create project structure
mkdir -p src data/memories scripts teams-app/icons

# Copy .env.example to .env and fill in values
cp .env.example .env

# Install dependencies
uv pip install -e .

# Run the application
uv run python app.py
```

### 3. Teams Deployment
1. Package Teams app:
   - Update manifest.json with your bot IDs
   - Add icon files (color-icon.png, outline-icon.png)
   - Zip the teams-app folder

2. Deploy to Teams:
   - Go to Teams Admin Center
   - Upload custom app
   - Add bots to desired channels

### 4. Testing
- Start with both bots in a test channel
- Send "Hello @Nous and @Claude" to test mentions
- Observe natural conversation flow
- Check if bots react to messages
- Verify bot-to-bot interactions

## Testing Scenarios

1. **Basic Functionality**:
   - Both bots respond when mentioned
   - Bots take turns naturally
   - Memory persists across sessions

2. **Reactions**:
   - Bots react to positive messages with 👍 or ❤️
   - Bots react to questions with 🤔
   - Bots react to each other's insights with 💡

3. **Complex Interactions**:
   - Ask a question that benefits from multiple perspectives
   - Watch bots build on each other's responses
   - Test memory recall with "What did we discuss earlier about X?"

## Success Metrics

- MVP is successful when:
  1. Two different LLM bots can join a Teams channel
  2. Bots respond naturally without responding to every message
  3. Bots can react to messages with emojis
  4. Bots interact with each other (messages and reactions)
  5. Bots remember context from earlier in conversation

## Future Enhancements (Post-MVP)

1. **Memory Improvements**:
   - Shared memory pool for team knowledge
   - Memory consolidation and pruning
   - Semantic memory organization

2. **Advanced Interactions**:
   - Typing indicators while bot is "thinking"
   - Thread-aware responses
   - File and image handling

3. **Management Features**:
   - Web dashboard for memory management
   - Cost tracking per bot/model
   - Analytics on bot participation

4. **Scale & Performance**:
   - Redis for conversation state
   - Horizontal scaling with multiple workers
   - Rate limiting and queueing

## Development Notes for Claude Code

### Key Implementation Priorities
1. Start with basic message handling (no reactions)
2. Add OpenRouter integration
3. Implement memory system
4. Add reaction capability
5. Fine-tune participation logic

### Common Gotchas
- Bot Framework requires specific activity format for reactions
- Teams may cache bot profiles - changes might not appear immediately
- Memory embeddings should be generated asynchronously to avoid blocking
- OpenRouter API key goes in Authorization header as "Bearer {key}"
- Each bot needs separate Azure registration (can't share App IDs)

### Testing Without Teams
Create a simple console client that simulates Teams messages:
```python
# scripts/test_bot.py
async def test_conversation():
    bot1 = MultiLLMBot(BOT_CONFIGS["nous_bot"])
    bot2 = MultiLLMBot(BOT_CONFIGS["claude_bot"])
    
    # Simulate conversation
    messages = [
        {"sender": "Human", "text": "What's the best programming language?"},
        # Bots respond...
    ]
```

This PRD provides everything needed to build a working MVP of the multi-LLM Teams chat system. The implementation should focus on getting basic message exchange working first, then layering on reactions and memory capabilities.
