"""Image processing utilities for vision and image generation."""

import base64
import io
import logging
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "webp", "gif"}

# Maximum dimensions to keep images under LLM limits
# Most vision models work well with images up to 2048x2048
MAX_IMAGE_DIMENSION = 2048

# Maximum file size for downloads (10 MB)
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


class ImageProcessingError(Exception):
    """Raised when image processing fails."""
    pass


async def download_image(url: str, timeout: int = 30) -> bytes:
    """
    Download an image from a URL.

    Args:
        url: Image URL to download
        timeout: Request timeout in seconds

    Returns:
        Raw image bytes

    Raises:
        ImageProcessingError: If download fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status != 200:
                    raise ImageProcessingError(
                        f"Failed to download image: HTTP {response.status}"
                    )

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if not content_type.startswith("image/"):
                    raise ImageProcessingError(
                        f"URL does not point to an image (content-type: {content_type})"
                    )

                # Read with size limit
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                    raise ImageProcessingError(
                        f"Image too large: {content_length} bytes (max: {MAX_DOWNLOAD_SIZE})"
                    )

                image_data = await response.read()

                if len(image_data) > MAX_DOWNLOAD_SIZE:
                    raise ImageProcessingError(
                        f"Image too large: {len(image_data)} bytes (max: {MAX_DOWNLOAD_SIZE})"
                    )

                return image_data

    except aiohttp.ClientError as e:
        raise ImageProcessingError(f"Network error downloading image: {e}")
    except Exception as e:
        raise ImageProcessingError(f"Failed to download image: {e}")


def validate_image_format(image_data: bytes) -> str:
    """
    Validate image format and return the format type.

    Args:
        image_data: Raw image bytes

    Returns:
        Image format (e.g., "png", "jpeg")

    Raises:
        ImageProcessingError: If format is not supported
    """
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            format_lower = img.format.lower() if img.format else "unknown"

            if format_lower not in SUPPORTED_FORMATS:
                raise ImageProcessingError(
                    f"Unsupported image format: {format_lower}. "
                    f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
                )

            return format_lower

    except Exception as e:
        raise ImageProcessingError(f"Failed to validate image: {e}")


def resize_image(image_data: bytes, max_dimension: int = MAX_IMAGE_DIMENSION) -> bytes:
    """
    Resize image if it exceeds maximum dimensions while preserving aspect ratio.

    Args:
        image_data: Raw image bytes
        max_dimension: Maximum width or height

    Returns:
        Resized image bytes (or original if already small enough)

    Raises:
        ImageProcessingError: If resizing fails
    """
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            width, height = img.size

            # Check if resizing needed
            if width <= max_dimension and height <= max_dimension:
                logger.debug(f"Image size {width}x{height} within limits, no resize needed")
                return image_data

            # Calculate new dimensions preserving aspect ratio
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")

            # Resize image
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to bytes
            output = io.BytesIO()

            # Preserve format, convert RGBA to RGB for JPEG
            save_format = img.format or "PNG"
            if save_format.upper() == "JPEG" and resized.mode == "RGBA":
                resized = resized.convert("RGB")

            resized.save(output, format=save_format)
            return output.getvalue()

    except Exception as e:
        raise ImageProcessingError(f"Failed to resize image: {e}")


def encode_image_to_base64(image_data: bytes, image_format: str) -> str:
    """
    Encode image to base64 with proper MIME type prefix for OpenRouter.

    Args:
        image_data: Raw image bytes
        image_format: Image format (e.g., "png", "jpeg")

    Returns:
        Data URL string (e.g., "data:image/png;base64,...")
    """
    base64_data = base64.b64encode(image_data).decode("utf-8")

    # Normalize format name for MIME type
    mime_type = "image/jpeg" if image_format == "jpg" else f"image/{image_format}"

    return f"data:{mime_type};base64,{base64_data}"


async def process_image_url(url: str) -> dict:
    """
    Download, validate, resize, and encode an image URL for LLM vision input.

    Args:
        url: Image URL to process

    Returns:
        Dict with 'type' and 'image_url' keys formatted for OpenRouter API

    Raises:
        ImageProcessingError: If any processing step fails
    """
    try:
        # Download image
        logger.info(f"Downloading image from {url}")
        image_data = await download_image(url)

        # Validate format
        image_format = validate_image_format(image_data)
        logger.debug(f"Image format: {image_format}")

        # Resize if needed
        resized_data = resize_image(image_data)

        # Encode to base64
        data_url = encode_image_to_base64(resized_data, image_format)

        logger.info(f"Successfully processed image from {url}")

        return {
            "type": "image_url",
            "image_url": {
                "url": data_url
            }
        }

    except ImageProcessingError:
        raise
    except Exception as e:
        raise ImageProcessingError(f"Unexpected error processing image: {e}")


def is_image_url(url: str) -> bool:
    """
    Check if a URL likely points to an image based on extension.

    Args:
        url: URL to check

    Returns:
        True if URL appears to be an image
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Check file extension
        for fmt in SUPPORTED_FORMATS:
            if path.endswith(f".{fmt}"):
                return True

        return False

    except Exception:
        return False


async def process_discord_attachment(attachment) -> Optional[dict]:
    """
    Process a Discord attachment for vision input.

    Args:
        attachment: Discord attachment object

    Returns:
        Dict formatted for OpenRouter API, or None if not an image
    """
    try:
        # Check if attachment is an image
        if not attachment.content_type or not attachment.content_type.startswith("image/"):
            logger.debug(f"Skipping non-image attachment: {attachment.filename}")
            return None

        # Extract format from content type
        image_format = attachment.content_type.split("/")[1].lower()

        if image_format not in SUPPORTED_FORMATS:
            logger.warning(
                f"Unsupported image format: {image_format} for {attachment.filename}"
            )
            return None

        # Process the attachment URL
        return await process_image_url(attachment.url)

    except Exception as e:
        logger.error(f"Failed to process Discord attachment: {e}", exc_info=True)
        return None
