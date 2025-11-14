# Bot Configuration Directory

This directory contains directory-based bot packages. Each bot is defined in its own subdirectory with configuration and prompt files.

## Directory Structure

```
bots/
├── nous/                  # Nous bot configuration
│   ├── config.json       # Bot configuration
│   └── prompt.txt        # System prompt
├── claude/               # Claude bot configuration
│   ├── config.json
│   └── prompt.txt
└── _example/             # Example template (not loaded)
    ├── config.json
    └── prompt.txt
```

## Adding a New Bot

1. **Create a new directory** under `bots/` with your bot's name (e.g., `bots/gpt4/`)

2. **Create `config.json`** with the following structure:

```json
{
  "bot_id": "discord_gpt4",
  "name": "GPT-4",
  "model": "openai/gpt-4o",
  "discord_token_env": "DISCORD_GPT4_TOKEN",
  "app_id_env": "GPT4_BOT_APP_ID",
  "app_password_env": "GPT4_BOT_APP_PASSWORD",
  "max_messages": 40,
  "max_verbatim_messages": 30,
  "max_decision_context": 10,
  "max_tokens_response": 800,
  "max_tokens_decision": 10,
  "enable_tools": true,
  "supports_vision": false
}
```

3. **Create `prompt.txt`** with your bot's system prompt:

```
You are GPT-4, an AI assistant participating in a Discord chat...
```

4. **Add environment variables** to your `.env` file:

```bash
DISCORD_GPT4_TOKEN=your_discord_token_here
GPT4_BOT_APP_ID=your_app_id_here
GPT4_BOT_APP_PASSWORD=your_app_password_here
```

5. **Run the bot**:

```bash
# Load all bots
uv run python discord_app.py

# Load specific bots only
ACTIVE_BOTS=gpt4,claude uv run python discord_app.py
```

## Configuration Fields

### Required Fields

- **bot_id**: Unique identifier for the bot (e.g., `discord_gpt4`)
- **name**: Display name for the bot (e.g., `GPT-4`)
- **model**: OpenRouter model identifier (e.g., `openai/gpt-4o`)
- **discord_token_env**: Name of environment variable containing Discord token
- **app_id_env**: Name of environment variable containing Azure App ID (for Teams)
- **app_password_env**: Name of environment variable containing Azure App Password (for Teams)

### Optional Fields

- **max_messages** (default: 10): Maximum messages to include in context
- **max_verbatim_messages** (default: 30): Maximum messages before auto-summarization
- **max_decision_context** (default: 5): Messages to consider for response decision
- **max_tokens_response** (default: 500): Max tokens for responses
- **max_tokens_decision** (default: 10): Max tokens for participation decision
- **enable_tools** (default: false): Enable tool calling (web search, image generation)
- **supports_vision** (default: false): Enable image vision capabilities

## Active Bot Selection

Control which bots run using the `ACTIVE_BOTS` environment variable:

```bash
# Load all bots in bots/ directory
uv run python discord_app.py

# Load only Nous
ACTIVE_BOTS=nous uv run python discord_app.py

# Load multiple specific bots
ACTIVE_BOTS=nous,claude uv run python discord_app.py
```

Or add to your `.env` file:

```bash
ACTIVE_BOTS=nous,claude
```

## Available Models

Check [OpenRouter](https://openrouter.ai/models) for available models. Popular options:

- **Anthropic**: `anthropic/claude-sonnet-4-5`, `anthropic/claude-opus-4`
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4-turbo`
- **Nous Research**: `nousresearch/hermes-4-405b`
- **Google**: `google/gemini-2-5-flash`
- **Meta**: `meta-llama/llama-4-70b`

## Vision Support

Models that support vision (can analyze images):

- `anthropic/claude-sonnet-4-5`
- `openai/gpt-4o`
- `google/gemini-2-5-flash`

Set `"supports_vision": true` in config.json for these models.

## Tool Calling

When `"enable_tools": true`, bots have access to:

- **Web Search**: Search the internet using Tavily API
- **Image Generation**: Create images using Gemini 2.5 Flash

## Example: Adding a Gemini Bot

1. Create directory:
```bash
mkdir -p bots/gemini
```

2. Create `bots/gemini/config.json`:
```json
{
  "bot_id": "discord_gemini",
  "name": "Gemini",
  "model": "google/gemini-2-5-flash",
  "discord_token_env": "DISCORD_GEMINI_TOKEN",
  "app_id_env": "GEMINI_BOT_APP_ID",
  "app_password_env": "GEMINI_BOT_APP_PASSWORD",
  "max_messages": 50,
  "max_tokens_response": 1000,
  "enable_tools": true,
  "supports_vision": true
}
```

3. Create `bots/gemini/prompt.txt`:
```
You are Gemini, a multimodal AI assistant. You can see images, search the web, and generate images to help users.
```

4. Add to `.env`:
```bash
DISCORD_GEMINI_TOKEN=your_token_here
GEMINI_BOT_APP_ID=your_app_id
GEMINI_BOT_APP_PASSWORD=your_password
```

5. Run:
```bash
ACTIVE_BOTS=gemini uv run python discord_app.py
```

## Notes

- Directories starting with `_` (like `_example`) are ignored by the loader
- Each bot maintains separate memory in `data/memories/{bot_id}.db`
- Bot names in `ACTIVE_BOTS` must match directory names exactly
- Invalid bot names trigger warnings but don't prevent other bots from loading
