# Image Support Implementation

## Overview

The Chorus bot system now supports both **image input** (vision) and **image generation** for Discord bots. Bots can see, analyze, and respond to images posted in channels, AND they can create and post their own images!

## Features Implemented

### ✅ Stage 6: Image Input (Complete)
### ✅ Stage 7: Image Generation (Complete)

#### Image Processing (`src/image_utils.py`)
- **Download images** from URLs with timeout and size limits (max 10MB)
- **Format validation** for PNG, JPEG, WebP, and GIF
- **Automatic resizing** to stay under LLM limits (max 2048x2048)
- **Base64 encoding** with proper MIME type prefixes
- **Discord attachment processing** with automatic format detection
- **Error handling** for unsupported formats and network issues

#### LLM Client Updates (`src/llm_client.py`)
- **Multi-modal message support** - text + images in same message
- **Vision API integration** with OpenRouter's format
- New `_build_message_content()` helper for multi-modal content
- Updated `get_response()` to accept images parameter
- Updated `get_response_with_tools()` to accept images parameter

#### Discord Bot Integration (`src/discord_bot.py`)
- **Automatic attachment detection** in messages
- **Process all image attachments** from each message
- **Always respond** when images are present
- **Pass images to LLM** for analysis
- Default prompt if message has only images: "What's in this image?"

#### Configuration Updates (`src/config.py`)
- Updated system prompts for both bots
- Informed bots they have vision capabilities
- Encourages detailed image analysis

#### Dependencies (`pyproject.toml`)
- Added `pillow>=10.0.0` for image processing
- Added `aiofiles>=23.0.0` for async file operations

---

### ✅ Stage 7: Image Generation (Complete)

#### Image Generation Tool (`src/tools.py`)
- **Generate images via OpenRouter** using Gemini 2.5 Flash Image Preview
- **Function calling integration** - bot decides when to generate
- **Aspect ratio control** - 1:1, 16:9, 9:16, 4:3, 3:4
- **Error handling** for generation failures
- **Returns base64 data URLs** ready for posting

#### LLM Client Updates (`src/llm_client.py`)
- **Track generated images** during tool calling loop
- **Return dict format** with both text and generated_images
- **Collect multiple images** from tool calls
- **Pass images back** to Discord bot for posting

#### Discord Bot Integration (`src/discord_bot.py`)
- **Post generated images** as Discord file attachments
- **Parse base64 data URLs** from OpenRouter response
- **Multiple image support** - can post several images at once
- **Automatic format detection** from MIME type
- **Error recovery** if individual images fail

#### Configuration Updates (`src/config.py`)
- Updated system prompts for both bots
- Informed bots they can generate images
- Guidelines for when to use image generation
- Encourages creative and detailed prompts

## How It Works

### Vision Flow (Image Input)

### 1. User Posts Image
```
User: [uploads image.png] "What is this?"
```

### 2. Bot Processes Attachment
```python
# Discord bot detects attachment
for attachment in message.attachments:
    image_data = await process_discord_attachment(attachment)
    images.append(image_data)
```

### 3. Image Processing Pipeline
```python
# Download → Validate → Resize → Base64 Encode
image_data = await download_image(url)
format = validate_image_format(image_data)
resized = resize_image(image_data, max_dimension=2048)
encoded = encode_image_to_base64(resized, format)
```

### 4. Send to LLM
```python
# Multi-modal format for OpenRouter
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What is this?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,iVBORw0KG..."
                }
            }
        ]
    }
]
```

### 5. Bot Responds
```
Claude: "This image shows a red apple on a wooden table.
The lighting suggests it was taken in natural daylight..."
```

---

### Image Generation Flow

### 1. User Requests Image
```
User: "Draw a futuristic spaceship"
```

### 2. LLM Decides to Use Tool
```python
# Bot recognizes this as an image generation request
# Calls generate_image tool with detailed prompt
{
    "tool": "generate_image",
    "args": {
        "prompt": "A sleek futuristic spaceship with metallic hull and glowing blue engines, flying through space with stars in the background, sci-fi concept art style",
        "aspect_ratio": "16:9"
    }
}
```

### 3. Generate Image via OpenRouter
```python
# tools.py calls OpenRouter API
response = await client.chat.completions.create(
    model="google/gemini-2.5-flash-image-preview",
    messages=[{"role": "user", "content": prompt}],
    modalities=["image", "text"],
    extra_body={"image_config": {"aspect_ratio": "16:9"}}
)
```

### 4. Extract Generated Images
```python
# llm_client.py collects images from tool result
generated_images = []
if tool_result.get("success") and tool_result.get("images"):
    generated_images.extend(tool_result["images"])
    # Images are base64 data URLs: "data:image/png;base64,iVBORw0..."
```

### 5. Bot Posts Images to Discord
```python
# discord_bot.py decodes and posts images
for data_url in generated_images:
    image_bytes = base64.b64decode(base64_data)
    file = discord.File(io.BytesIO(image_bytes), "generated_image.png")
    await channel.send(files=[file])
```

### 6. User Sees Image
```
Bot: "Here's a futuristic spaceship!"
     [Image appears in Discord]
```

## Bot Capabilities

### Currently Configured
- **Claude Bot**: `anthropic/claude-sonnet-4.5`
  - ✅ Vision (can see and analyze images)
  - ✅ Image Generation
  - ✅ Web Search
  - Best for: Visual analysis, thoughtful responses, creative generation

- **Nous Bot**: `nousresearch/hermes-4-405b`
  - ❌ Vision (text-only model)
  - ✅ Image Generation
  - ✅ Web Search
  - Best for: Pure reasoning, math, code, STEM problems

### Tag-Team Strategy
The bots complement each other:
- **Images posted**: Claude analyzes, Nous can reason about the analysis
- **Complex problems**: Nous handles logic/math, Claude provides context
- **Creative requests**: Both can generate images with different styles
- **Research**: Both can search the web and synthesize information

### Other OpenRouter Models with Vision
- `google/gemini-2.0-flash-001`
- `google/gemini-2.5-flash-preview`
- `openai/gpt-4o`
- Many more - check OpenRouter docs

## Usage Examples

### Vision (Image Input)

#### Example 1: Simple Image Query
```
User: [posts screenshot] "What's wrong with this code?"
Bot: Analyzes the image and identifies the bug
```

#### Example 2: Multiple Images
```
User: [posts 3 images] "Compare these designs"
Bot: Analyzes all three images and provides comparison
```

#### Example 3: Image + Text
```
User: [posts diagram] "Explain how this architecture works"
Bot: Detailed explanation based on the diagram
```

#### Example 4: Image Only
```
User: [posts meme.jpg]
Bot: Automatically prompts with "What's in this image?" and responds
```

### Image Generation

#### Example 5: Explicit Generation Request
```
User: "Can you draw a sunset over the ocean?"
Bot: "I'll create that for you!"
     *generates and posts image*
     "Here's a beautiful sunset over the ocean!"
```

#### Example 6: Proactive Generation
```
User: "What does the Fibonacci spiral look like?"
Bot: *generates image of Fibonacci spiral*
     "Here's a visual representation of the Fibonacci spiral..."
```

#### Example 7: Multiple Aspect Ratios
```
User: "Show me a landscape in 16:9 format"
Bot: *generates 16:9 landscape image*
     "Here's a wide-format landscape scene!"
```

#### Example 8: Creative Prompts
```
User: "Draw a cyberpunk city at night with neon lights"
Bot: *generates detailed cyberpunk scene*
     "I've created a cyberpunk city scene with vibrant neon lights..."
```

#### Example 9: Tag-Team Collaboration
```
User: [posts complex circuit diagram]
Claude: "This is a low-pass filter circuit with a cutoff frequency around 1kHz..."
Nous: "Based on Claude's analysis, the transfer function would be H(s) = 1/(1 + sRC)..."
```

#### Example 10: Image + Generation Workflow
```
User: [posts sketch] "Can you make a polished version of this?"
Claude: "I see a rough sketch of a dragon. Let me generate a refined version..."
     *generates polished dragon artwork*
Nous: "That looks great! The proportions and details really bring it to life."
```

## Testing

### Automated Tests

#### Image Processing Tests
Run the image processing tests:
```bash
uv run python scripts/test_image_processing.py
```

Tests verify:
- ✅ URL detection (PNG, JPG, JPEG, WebP, GIF)
- ✅ Image validation
- ✅ Resizing (3000x3000 → 2048x2048)
- ✅ Base64 encoding with MIME types

#### Image Generation Tests
Run the image generation tests:
```bash
uv run python scripts/test_image_generation.py
```

Tests verify:
- ✅ Image generation tool initialization
- ✅ API call to OpenRouter succeeds
- ✅ Base64 data URLs returned correctly
- ✅ Valid data URL format (data:image/png;base64,...)

### Manual Testing (Discord)

1. **Start Discord bot:**
```bash
uv run python discord_app.py
```

2. **Test Vision (Image Input):**
   - Post image in Discord channel where bot is active
   - Bot should detect, process, and analyze the image
   - Bot responds with description

3. **Test Image Generation:**
   - Ask bot: "Draw a sunset over the ocean"
   - Bot should generate and post an image
   - Image appears as Discord attachment

4. **Test Creative Prompts:**
   - Try: "Create a diagram showing how photosynthesis works"
   - Try: "Draw a cute robot eating pizza"
   - Try: "Generate a landscape in 16:9 format"

## Configuration

### Enable/Disable Vision
Vision is automatically enabled when:
1. Bot uses a vision-capable model
2. Message contains image attachments

No configuration flags needed - it just works!

### Enable/Disable Image Generation
Image generation is automatically enabled when:
1. OpenRouter API key is configured
2. Bot has `enable_tools=True` in config
3. Image generation tool is available

Both Discord bots have tools enabled by default!

### Image Processing Limits

In `src/image_utils.py`:
```python
MAX_IMAGE_DIMENSION = 2048  # Max width/height
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
```

Adjust these if needed for your use case.

## Architecture

```
┌─────────────────┐
│ Discord Message │
│  (with image)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ process_discord_    │
│   attachment()      │
│ - Check MIME type   │
│ - Download image    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Image Processing    │
│ - Validate format   │
│ - Resize if needed  │
│ - Encode base64     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ LLM Client          │
│ - Build multi-modal │
│   message content   │
│ - Send to OpenRouter│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Vision-capable LLM  │
│ (Claude, Gemini,    │
│  GPT-4o, etc.)      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Bot Response        │
│ (image analysis)    │
└─────────────────────┘
```

## File Changes

### New Files
- `src/image_utils.py` - Image processing utilities (284 lines)
- `scripts/test_image_processing.py` - Unit tests

### Modified Files
- `src/llm_client.py` - Added vision message support
- `src/discord_bot.py` - Added attachment handling
- `src/config.py` - Updated system prompts
- `pyproject.toml` - Added dependencies
- `IMPLEMENTATION_PLAN.md` - Documented progress

## Next Steps (Future Enhancements)

### Stage 8: Advanced Features
- **Memory Integration**: Store image descriptions and generation history
- **Cost Tracking**: Track API costs for vision and generation
- **More Formats**: Support additional image formats
- **Batch Processing**: Optimize multiple image operations
- **Conversation Context**: Include image history in conversations
- **Model Selection**: Let users choose different generation models
- **Style Presets**: Predefined styles for image generation

### Teams Integration (Future)
- Add attachment handling to `src/bot.py`
- Add image generation posting for Teams
- Update Teams manifest: `supportsFiles: true`
- Test with Microsoft Teams

### Advanced Generation Features (Future)
- **Edit Images**: Modify existing images
- **Image Variations**: Generate variations of an image
- **Inpainting**: Fill in parts of images
- **Upscaling**: Enhance image resolution
- **Style Transfer**: Apply artistic styles to images

## Known Limitations

1. **Teams not implemented** - Only Discord currently supported (both vision and generation)
2. **Nous bot has no vision** - By design: Hermes-4 is text-only. Only Claude can see images
3. **No memory integration** - Image descriptions and generation history not stored yet
4. **Single generation model** - Only Gemini 2.5 Flash for now
5. **No editing features** - Can only generate new images, not modify existing ones
6. **No cost tracking** - Vision and generation costs not monitored yet

Note: The Nous/Claude split is intentional - they complement each other as a tag-team!

## Troubleshooting

### "Unsupported image format"
- Check file extension (must be PNG, JPG, JPEG, WebP, or GIF)
- Verify MIME type is correct

### "Image too large"
- Images over 10MB are rejected
- Increase `MAX_DOWNLOAD_SIZE` if needed

### "Failed to download image"
- Check network connectivity
- Verify URL is accessible
- Check timeout settings (default 30s)

### Bot doesn't respond to images
- Verify bot has vision-capable model
- Check logs for processing errors
- Ensure Discord permissions allow reading attachments

### Bot doesn't generate images
- Check OpenRouter API key is configured
- Verify `enable_tools=True` in bot config
- Check logs for tool execution errors
- Ensure model supports image generation
- Check API quotas/limits on OpenRouter

### Generated images don't appear
- Check Discord bot has permission to attach files
- Verify base64 decoding is working (check logs)
- Ensure image data URLs are valid format
- Check for errors in `_post_generated_images`

## API Reference

### `process_discord_attachment(attachment)`
Process a Discord attachment for vision input.

**Parameters:**
- `attachment`: Discord attachment object

**Returns:**
- Dict formatted for OpenRouter API, or None if not an image

### `process_image_url(url)`
Download, validate, resize, and encode an image URL.

**Parameters:**
- `url`: Image URL to process

**Returns:**
- Dict with 'type' and 'image_url' keys

### `resize_image(image_data, max_dimension=2048)`
Resize image if it exceeds maximum dimensions.

**Parameters:**
- `image_data`: Raw image bytes
- `max_dimension`: Maximum width or height

**Returns:**
- Resized image bytes (or original if small enough)

### `ImageGenerationTool.generate_image(prompt, aspect_ratio="1:1", model=None)`
Generate an image from a text prompt.

**Parameters:**
- `prompt`: Description of the image to generate
- `aspect_ratio`: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
- `model`: Optional model override

**Returns:**
- Dict with 'success', 'images' (list of data URLs), 'text', 'model', 'prompt'

### `_post_generated_images(channel, image_data_urls)`
Post generated images to a Discord channel (Discord bot method).

**Parameters:**
- `channel`: Discord channel to post to
- `image_data_urls`: List of base64 data URLs

**Returns:**
- True if successfully posted

## Credits

Implemented following the development guidelines in `CLAUDE.md`:
- Incremental progress with passing tests
- Clear intent over clever code
- Learning from existing patterns
- Thorough error handling
- Test-driven development

**Stage 6 complete!** 🎉 Image Input (Vision)
**Stage 7 complete!** 🎉 Image Generation

Your bots can now see AND create! 🖼️✨
