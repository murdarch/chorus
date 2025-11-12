"""Test script for image generation functionality."""

import asyncio
import logging
from src.tools import get_image_gen_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_image_generation():
    """Test image generation tool."""

    print("\n=== Testing Image Generation Tool ===\n")

    # Get the image generation tool
    image_gen = get_image_gen_tool()

    if not image_gen.enabled:
        print("❌ Image generation tool is not enabled (no API key?)")
        return

    print(f"✅ Image generation tool initialized")
    print(f"   Model: {image_gen.default_model}\n")

    # Test 1: Simple image generation
    print("Test 1: Generate a simple image")
    print("-" * 50)

    result = await image_gen.generate_image(
        prompt="A cute red panda eating bamboo in a forest, digital art style",
        aspect_ratio="1:1"
    )

    if result.get("success"):
        images = result.get("images", [])
        print(f"✅ Successfully generated {len(images)} image(s)")

        for idx, img_url in enumerate(images):
            # Show first 100 chars of data URL
            print(f"\n   Image {idx + 1}:")
            print(f"   Data URL prefix: {img_url[:100]}...")
            print(f"   Total length: {len(img_url)} characters")

            # Check if it's a valid base64 data URL
            if img_url.startswith("data:image/"):
                header = img_url.split(",")[0]
                print(f"   Format: {header}")
                print(f"   ✅ Valid data URL format")
            else:
                print(f"   ❌ Invalid data URL format")

        if result.get("text"):
            print(f"\n   Model response: {result['text']}")

    else:
        print(f"❌ Image generation failed")
        print(f"   Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print("\n💡 Note: To fully test, run discord_app.py and ask a bot to:")
    print('   "Draw a sunset over the ocean"')
    print("   The bot should generate and post the image to Discord!")
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_image_generation())
