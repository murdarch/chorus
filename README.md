# Chorus

**Multi-LLM Discord bots that can see, create, and collaborate**

Chorus is an intelligent multi-bot system where AI assistants work together in Discord channels. They can analyze images, generate artwork, search the web, remember context, and naturally collaborate with each other and humans.

[![GitHub release](https://img.shields.io/github/v/release/murdarch/chorus)](https://github.com/murdarch/chorus/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Features

### Vision & Image Generation
- **See images**: Claude analyzes photos, screenshots, diagrams, and artwork
- **Create images**: Both bots generate images from text descriptions
- **Multi-modal**: Combines text and visual understanding seamlessly

### Tag-Team Collaboration
- **Claude**: Visual expert with thoughtful analysis and creative generation
- **Nous**: Reasoning powerhouse for math, code, and logical problems
- **Natural interaction**: Bots work together, complementing each other's strengths

### Smart Memory System
- Vector-based memory with sqlite-vss
- Remembers conversations across sessions
- Retrieves relevant context automatically
- Separate memory per bot

### Intelligent Features
- Web search integration (Tavily API)
- Smart participation logic (knows when to respond)
- Emoji reactions
- Auto-summarization for long conversations
- Tool calling with function support

---

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Discord bot tokens ([create bots here](https://discord.com/developers/applications))
- [OpenRouter API key](https://openrouter.ai/keys)

### Installation

```bash
# Clone the repository
git clone https://github.com/murdarch/chorus.git
cd chorus

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# OPENROUTER_API_KEY=your_key_here
# DISCORD_NOUS_TOKEN=your_token_here
# DISCORD_CLAUDE_TOKEN=your_token_here
```

### Configure Your Bots

Chorus uses a directory-based configuration system. Each bot lives in its own directory under `bots/`:

```bash
# Copy the example bot template
cp -r bots/_example bots/mybot

# Edit the configuration
nano bots/mybot/config.json  # Set model, tokens, capabilities
nano bots/mybot/prompt.txt   # Customize personality

# The bot will be automatically discovered and loaded!
```

See [bots/README.md](bots/README.md) for detailed configuration options.

### Run the Bots

```bash
# Start all configured bots
uv run python discord_app.py

# Or run specific bots only
ACTIVE_BOTS=nous,claude uv run python discord_app.py
```

That's it! Invite your bots to a Discord server and start chatting.

---

## Usage Examples

### Vision (Image Analysis)
```
You: [posts screenshot of code]
     "What's wrong with this function?"

Claude: "I can see the issue - you're missing a null check on line 23..."
```

### Image Generation
```
You: "Draw a sunset over the ocean"

Claude: *generates and posts beautiful sunset image*
       "Here's a serene sunset scene over calm waters..."
```

### Tag-Team Problem Solving
```
You: [posts circuit diagram]

Claude: "This is a low-pass filter with cutoff around 1kHz..."
Nous: "Based on the components, the transfer function is H(s) = 1/(1 + sRC)..."
```

### Creative Collaboration
```
You: "Both of you: draw a dragon!"

Nous: *generates stylized dragon*
Claude: *generates detailed fantasy dragon*

You: "I like Claude's better!"
Nous: "Fair point, Claude's got the artistic edge today"
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│               Discord Channels                   │
└───────────────┬─────────────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
    ┌───▼────┐      ┌───▼────┐
    │ Nous   │      │ Claude │
    │ Bot    │      │ Bot    │
    └───┬────┘      └───┬────┘
        │                │
        └────┬──────┬────┘
             │      │
    ┌────────▼──────▼─────────┐
    │   OpenRouter API         │
    │  - Hermes-4 405B (Nous) │
    │  - Claude Sonnet (Claude)│
    │  - Gemini (Generation)   │
    └──────────────────────────┘
             │
    ┌────────▼──────────┐
    │  Supporting APIs   │
    │  - Tavily (Search) │
    │  - Image Processing│
    └────────────────────┘
             │
    ┌────────▼─────────┐
    │  Local Storage   │
    │  - SQLite + VSS  │
    │  - Memories      │
    └──────────────────┘
```

---

## Bot Capabilities

| Feature | Claude (Sonnet 4.5) | Nous (Hermes-4 405B) |
|---------|---------------------|----------------------|
| **Vision** | Yes - Can see images | No - Text-only |
| **Image Generation** | Yes - Creates images | Yes - Creates images |
| **Web Search** | Yes - Tavily API | Yes - Tavily API |
| **Memory** | Yes - Vector memory | Yes - Vector memory |
| **Best For** | Visual analysis, creative work | Math, code, logic, reasoning |

The bots complement each other perfectly - Claude handles visual tasks while Nous excels at pure reasoning!

---

## Documentation

- **[Bot Configuration](bots/README.md)** - Add and configure custom bots
- **[Setup Guide](DISCORD_SETUP.md)** - Detailed Discord bot configuration
- **[Image Support](IMAGE_SUPPORT.md)** - Vision and generation features
- **[Deployment](DEPLOYMENT.md)** - Production deployment guide
- **[Resetting Bots](docs/resetting_bots.md)** - Clear bot memories and troubleshooting
- **[PRD](PRD.md)** - Product requirements and design decisions

---

## Tech Stack

- **Language**: Python 3.11+
- **Bot Framework**: discord.py
- **LLM Gateway**: OpenRouter
- **Models**: Claude Sonnet 4.5, Hermes-4 405B, Gemini 2.5 Flash
- **Memory**: SQLite + sqlite-vss
- **Embeddings**: sentence-transformers
- **Image Processing**: Pillow
- **Web Search**: Tavily API
- **Package Manager**: uv

---

## Roadmap

### Completed
- [x] Multi-bot system with intelligent participation
- [x] Vector memory with conversation recall
- [x] Image vision (Claude can see images)
- [x] Image generation (both bots create images)
- [x] Web search integration
- [x] Emoji reactions
- [x] Discord integration
- [x] Directory-based bot configuration (add bots without code changes)

### Coming Soon
- [ ] Memory integration for images
- [ ] Cost tracking and analytics
- [ ] Microsoft Teams support
- [ ] More generation models
- [ ] Image editing features
- [ ] Custom tool creation

---

## Contributing

Contributions are welcome! Here are some ways to help:

- Report bugs and issues
- Suggest new features
- Improve documentation
- Submit pull requests

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and development process.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **OpenRouter** for unified LLM API access
- **Anthropic** for Claude Sonnet 4.5
- **Nous Research** for Hermes-4 405B
- **Google** for Gemini models
- **Discord** for the excellent bot platform

---

## Support

- Issues: [GitHub Issues](https://github.com/murdarch/chorus/issues)
- Discussions: [GitHub Discussions](https://github.com/murdarch/chorus/discussions)

---

**Built with Claude Code**

Chorus brings together the best LLMs to create a collaborative, intelligent, and visually-aware bot experience. Watch your bots work together, learn from conversations, and surprise you with their creativity!
