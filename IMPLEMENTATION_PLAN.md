# Chorus Implementation Plan

## Overview
Build a Microsoft Teams multi-LLM bot system where multiple AI bots (via OpenRouter) participate naturally in conversations, interacting with humans and each other through messages and emoji reactions.

---

## Stage 1: Foundation & Project Setup
**Goal**: Establish project structure, install dependencies, and create basic configuration system
**Status**: Complete

### Success Criteria
- [x] Project structure matches PRD specification
- [x] All dependencies installed via uv
- [x] Configuration system loads environment variables
- [x] Basic logging configured
- [x] .env.example template created

### Implementation Tasks
1. Create directory structure (src/, data/memories/, scripts/, teams-app/)
2. Update pyproject.toml with all dependencies from PRD
3. Install dependencies with `uv sync`
4. Create src/__init__.py
5. Implement src/config.py with bot configurations
6. Create .env.example with all required variables
7. Set up basic logging configuration

### Tests
- [x] Can import config module
- [x] Config loads environment variables correctly
- [x] Config raises appropriate errors for missing required vars
- [x] All dependencies import successfully

### Files to Create/Modify
- `pyproject.toml` - Add dependencies
- `src/__init__.py` - Package initialization
- `src/config.py` - Configuration and bot profiles
- `.env.example` - Environment variable template
- `data/memories/.gitkeep` - Ensure directory exists
- `scripts/.gitkeep` - Ensure directory exists
- `teams-app/.gitkeep` - Ensure directory exists

---

## Stage 2: Basic Bot Framework Integration
**Goal**: Single bot that can receive and acknowledge Teams messages (no LLM yet)
**Status**: Complete

### Success Criteria
- [x] Bot Framework adapter configured for one bot
- [x] Web server running on port 3978
- [x] Bot receives messages via /api/messages/nous_bot endpoint
- [x] Bot sends simple echo responses
- [x] Basic conversation history tracking working

### Implementation Tasks
1. Create app.py with aiohttp web server
2. Set up Bot Framework adapter with authentication
3. Implement basic bot class in src/bot.py
4. Add message routing to appropriate bot
5. Implement conversation history tracking (in-memory for now)
6. Add proper error handling and logging

### Tests
- [x] Server starts without errors
- [x] POST to /api/messages/nous_bot with valid activity succeeds
- [x] Bot responds with echo message
- [x] Invalid authentication is rejected
- [x] Conversation history tracks messages per conversation ID
- [x] Bot ignores its own messages

### Files to Create/Modify
- `app.py` - Main application entry point
- `src/bot.py` - Main bot class with message handling
- Create manual test script for validation

---

## Stage 3: OpenRouter LLM Integration
**Goal**: Bot generates intelligent responses using OpenRouter API
**Status**: Complete

### Success Criteria
- [x] OpenRouter client successfully calls API
- [x] Bot uses LLM to generate contextual responses
- [x] Conversation history included in LLM context (last 10 messages)
- [x] Bot makes intelligent decisions about when to respond
- [x] Different models work for different bot configurations

### Implementation Tasks
1. Implement src/llm_client.py with AsyncOpenAI client
2. Add get_completion() method with proper error handling
3. Add should_respond() method for participation logic
4. Update bot.py to use LLM for responses
5. Implement direct mention detection (always respond)
6. Add logic to avoid responding twice in a row
7. Add temperature configuration per request type

### Tests
- [x] LLM client connects to OpenRouter successfully
- [x] get_completion() returns valid responses
- [x] should_respond() makes reasonable decisions
- [x] Bot responds to direct mentions
- [x] Bot doesn't respond to consecutive messages
- [x] Bot uses last 10 messages for context
- [x] Different models can be configured per bot

### Files to Create/Modify
- `src/llm_client.py` - OpenRouter integration
- `src/bot.py` - Update to use LLM client
- `scripts/test_bot.py` - Console test script

---

## Stage 4: Memory System with Vector Search
**Goal**: Bots remember context across conversations using SQLite-vss
**Status**: Complete

### Success Criteria
- [x] SQLite database created per bot with sqlite-vss extension
- [x] Vector embeddings generated using sentence-transformers
- [x] Memories stored with content, type, timestamp, confidence
- [x] Vector similarity search returns relevant memories
- [x] Memories included in LLM system prompt
- [x] Important information extracted and stored after responses

### Implementation Tasks
1. Implement src/memory.py with MemorySystem class
2. Set up SQLite database schema with vss extension
3. Initialize sentence-transformers model (all-MiniLM-L6-v2)
4. Implement store_memory() with embedding generation
5. Implement search_memories() with vector similarity
6. Implement process_for_memories() to extract important info
7. Update bot.py to retrieve and use memories
8. Add async embedding generation to avoid blocking

### Tests
- [x] Database initializes with correct schema
- [x] Embeddings generated with correct dimensions (384)
- [x] Memories stored successfully
- [x] Vector search returns relevant results
- [x] Memory retrieval happens before response generation
- [x] Memories persist across bot restarts
- [x] Multiple bots have separate memory stores

### Files to Create/Modify
- `src/memory.py` - SQLite-vss memory system
- `src/bot.py` - Integrate memory retrieval and storage
- Add tests for memory operations

---

## Stage 5: Multi-Bot System & Emoji Reactions
**Goal**: Second bot added, bots interact with each other, emoji reactions working
**Status**: Complete

### Success Criteria
- [x] Two bots running simultaneously (Nous + Claude)
- [x] Each bot has separate endpoint and configuration
- [x] Bots can see and respond to each other's messages
- [x] Emoji reaction system implemented
- [x] Bots react appropriately to messages (30% chance)
- [x] Natural delays added for reactions (1-3 seconds)
- [x] Bot-to-bot conversations flow naturally

### Implementation Tasks
1. Add second bot configuration (Claude)
2. Create separate endpoints for each bot
3. Implement src/reactions.py with reaction logic
4. Add get_reaction() method to LLM client
5. Implement Teams reaction activity format
6. Add 30% random chance for reaction consideration
7. Add 1-3 second delay before reactions
8. Update participation logic to account for bot-to-bot interaction
9. Test multi-bot conversation scenarios

### Tests
- [x] Both bots start successfully
- [x] Bots have separate /api/messages endpoints
- [x] Bot A sees messages from Bot B
- [x] Bot B responds to Bot A's messages
- [x] Reactions post successfully (logged for Teams)
- [x] Reaction emoji selection is contextually appropriate
- [x] Both humans and bots receive reactions
- [x] Bots maintain separate memories
- [x] Three-way conversations work (human + 2 bots)

### Files to Create/Modify
- `src/reactions.py` - Reaction decision logic
- `src/llm_client.py` - Add get_reaction() method
- `src/bot.py` - Integrate reaction capabilities
- `src/config.py` - Add second bot configuration
- `app.py` - Add second bot endpoint and adapter
- `scripts/test_bot.py` - Test multi-bot scenarios

---

## Stage 6: Image Input - Receiving and Processing
**Goal**: Enable bots to receive and analyze images posted in channels
**Status**: Complete (Discord only - Teams skipped for now)

### Success Criteria
- [x] Bots can detect image attachments from Discord
- [x] Images are downloaded and converted to base64
- [x] Images are passed to vision-capable LLMs for analysis
- [x] Both inline images and file attachments supported
- [x] Image processing utilities created and tested

### Implementation Tasks
1. ~~Add attachment handling to Teams bot (bot.py)~~ - Skipped
2. Add attachment handling to Discord bot (discord_bot.py) - ✅ Complete
3. Create image processing utility (download, resize, base64 encode) - ✅ Complete
4. Update LLM client to support vision messages (multi-modal content) - ✅ Complete
5. Handle multiple attachments per message - ✅ Complete
6. Add image URL support (inline images) - ✅ Complete
7. Update system prompts to inform bots about vision capabilities - ✅ Complete

### Tests
- [x] Image processing utilities tested (URL detection, resize, base64 encoding)
- [x] Large images properly resized to 2048x2048 max
- [ ] Post image in Discord channel, bot responds with description (manual test needed)
- [ ] Post multiple images, bot handles all of them (manual test needed)

### Files to Create/Modify
- `src/image_utils.py` - Image processing utilities ✅
- `src/bot.py` - Add attachment handling (skipped - Teams)
- `src/discord_bot.py` - Add attachment handling ✅
- `src/llm_client.py` - Add vision message support ✅
- `pyproject.toml` - Add Pillow dependency ✅

### Notes
- **Bot capability split**: Claude has vision, Nous doesn't (by design)
- Hermes-4-405b is text-only, so Nous can't see images
- Tag-team approach: Claude analyzes images, Nous reasons about them
- Both bots can generate images via tool calling

---

## Stage 7: Image Output - Generation Capabilities
**Goal**: Enable bots to generate and post images using image-generation models
**Status**: Complete (Discord only - Teams skipped for now)

### Success Criteria
- [x] Bots can generate images via OpenRouter
- [x] Generated images are posted to Discord
- [x] Tool calling integration for image generation
- [x] Bot decides when image generation is appropriate
- [x] System prompts updated to inform bots about generation capability

### Implementation Tasks
1. Research OpenRouter image generation models (Gemini 2.5 Flash) - ✅ Complete
2. Add image generation tool to tools.py - ✅ Complete
3. ~~Implement Teams image posting~~ - Skipped
4. Implement Discord image posting (file upload) - ✅ Complete
5. Add decision logic for when to generate images - ✅ Complete (via tool description)
6. Handle generation errors gracefully - ✅ Complete
7. Update llm_client to track and return generated images - ✅ Complete
8. Update system prompts with image generation guidance - ✅ Complete

### Tests
- [x] Image generation tool initialized and working
- [x] Base64 data URL parsing implemented
- [x] Discord file upload from base64 implemented
- [ ] Ask bot to "draw a sunset", bot generates and posts image (manual test needed)
- [ ] Multiple images handled correctly (manual test needed)
- [ ] Generation failures are handled gracefully

### Files to Create/Modify
- `src/tools.py` - Add image generation tool ✅
- `src/llm_client.py` - Return dict with text + generated_images ✅
- `src/discord_bot.py` - Add image posting for Discord ✅
- `src/config.py` - Update system prompts ✅
- `scripts/test_image_generation.py` - Test script ✅

---

## Stage 8: Configuration, Memory, and Polish
**Goal**: Update configuration, memory integration, and robust error handling
**Status**: Not Started

### Success Criteria
- [ ] Teams manifest updated to support files
- [ ] Feature flags for enabling/disabling image features
- [ ] Image descriptions stored in memory
- [ ] Graceful handling of unsupported formats
- [ ] Performance optimization for large images

### Implementation Tasks
1. Update Teams manifest: supportsFiles: true
2. Add feature flags: enable_vision, enable_image_generation
3. Add image size/quality settings to config
4. Store image analysis in memory system
5. Add metadata for image attachments
6. Add file size limits and format validation
7. Implement image resizing to stay under LLM limits
8. Add logging for image operations
9. Add timeout handling for downloads

### Tests
- [ ] Configuration validates correctly
- [ ] Bots respect feature flags
- [ ] Image descriptions appear in memory search results
- [ ] Post unsupported format, bot explains limitation
- [ ] Post very large image, bot resizes appropriately
- [ ] Image context included in conversation history

### Files to Create/Modify
- `teams-app/manifest.json` - Enable file support
- `src/config.py` - Add image feature flags
- `src/memory.py` - Store image context
- `src/image_utils.py` - Add validation and resizing
- All bot files - Add error handling

---

## Post-MVP Enhancements (Future)

### Teams App Manifest
- Create manifest.json with both bot registrations
- Add app icons (color and outline)
- Package as Teams app zip

### Azure Deployment
- Document Azure Bot Service registration process
- Create setup_azure.py helper script
- Configure messaging endpoints
- Test in actual Teams environment

### Performance & Reliability
- Add rate limiting
- Implement request queueing
- Add cost tracking per bot/model
- Memory consolidation and pruning
- Shared memory pool for team knowledge

### Advanced Features
- Typing indicators while "thinking"
- Thread-aware responses
- File and image handling
- Web dashboard for memory management
- Analytics on bot participation

---

## Development Notes

### Current Focus
✓ Stage 1 Complete - Foundation & Project Setup
✓ Stage 2 Complete - Basic Bot Framework Integration
✓ Stage 3 Complete - OpenRouter LLM Integration
✓ Stage 4 Complete - Memory System with Vector Search
✓ Stage 5 Complete - Multi-Bot System & Emoji Reactions

🎉 MVP COMPLETE! All stages finished successfully!

### Key Principles
- Each stage must compile and pass all tests before moving to next
- Commit after each completed stage
- If stuck after 3 attempts, document and reassess approach
- Follow existing Python patterns and conventions
- Use uv for all dependency management

### Testing Strategy
- Write tests before implementation where possible
- Manual console testing for interactive features
- Integration tests for multi-bot scenarios
- Test without Teams first using scripts/test_bot.py

### Common Gotchas from PRD
- Bot Framework requires specific activity format for reactions
- Memory embeddings should be async to avoid blocking
- OpenRouter API key goes in Authorization header as "Bearer {key}"
- Each bot needs separate Azure registration
- Don't respond to own messages (check sender ID)
