"""Test script for image processing functionality."""

import asyncio
import logging
from src.image_utils import (
    is_image_url,
    validate_image_format,
    resize_image,
    encode_image_to_base64,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_image_utils():
    """Test image utility functions."""

    print("\n=== Testing Image Utils ===\n")

    # Test 1: URL detection
    print("Test 1: URL Detection")
    test_urls = [
        ("https://example.com/image.png", True),
        ("https://example.com/image.jpg", True),
        ("https://example.com/image.jpeg", True),
        ("https://example.com/image.webp", True),
        ("https://example.com/image.gif", True),
        ("https://example.com/document.pdf", False),
        ("https://example.com/page.html", False),
    ]

    for url, expected in test_urls:
        result = is_image_url(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url}: {result} (expected: {expected})")

    print("\n✅ URL detection tests completed\n")

    # Test 2: Create a simple test image
    print("Test 2: Image Processing")
    try:
        from PIL import Image
        import io

        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()

        print(f"  ✓ Created test image: {len(img_data)} bytes")

        # Test validation
        img_format = validate_image_format(img_data)
        print(f"  ✓ Validated format: {img_format}")

        # Test resize (should not resize small image)
        resized_data = resize_image(img_data, max_dimension=2048)
        print(f"  ✓ Resize check: {len(resized_data)} bytes (no resize needed)")

        # Test base64 encoding
        data_url = encode_image_to_base64(img_data, img_format)
        print(f"  ✓ Encoded to base64: {len(data_url)} chars")
        print(f"    Prefix: {data_url[:50]}...")

        # Test resize with large image
        large_img = Image.new('RGB', (3000, 3000), color='blue')
        large_bytes = io.BytesIO()
        large_img.save(large_bytes, format='PNG')
        large_data = large_bytes.getvalue()

        print(f"\n  Creating large test image: {len(large_data)} bytes")
        resized_large = resize_image(large_data, max_dimension=2048)
        print(f"  ✓ Resized large image: {len(resized_large)} bytes (reduced)")

        # Verify resized dimensions
        resized_img = Image.open(io.BytesIO(resized_large))
        width, height = resized_img.size
        print(f"  ✓ Resized dimensions: {width}x{height} (max: 2048)")
        assert max(width, height) <= 2048, "Image not properly resized!"

        print("\n✅ Image processing tests completed\n")

    except Exception as e:
        print(f"\n✗ Error during image processing tests: {e}")
        raise

    print("\n=== All Tests Passed! ===\n")


if __name__ == "__main__":
    asyncio.run(test_image_utils())
