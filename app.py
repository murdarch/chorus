"""Main application entry point for Chorus bot system."""

import logging
from aiohttp import web
from aiohttp.web import Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

from src.config import get_settings, get_bot_config
from src.bot import ChorusBot

# Logger
logger = logging.getLogger(__name__)


class BotEndpoint:
    """Handles routing for a single bot endpoint."""

    def __init__(self, bot_id: str):
        """Initialize bot endpoint with specific bot configuration."""
        self.bot_id = bot_id
        self.bot_config = get_bot_config(bot_id)

        # Create Bot Framework adapter
        settings = BotFrameworkAdapterSettings(
            app_id=self.bot_config.app_id,
            app_password=self.bot_config.app_password,
        )
        self.adapter = BotFrameworkAdapter(settings)

        # Create bot instance
        self.bot = ChorusBot(self.bot_config)

        # Error handler for adapter
        async def on_error(context: TurnContext, error: Exception):
            logger.error(f"[{self.bot_id}] Error: {error}", exc_info=True)
            await context.send_activity("Sorry, I encountered an error processing your message.")

        self.adapter.on_turn_error = on_error

        logger.info(f"Initialized bot endpoint: {bot_id} ({self.bot_config.name})")

    async def handle_message(self, req: Request) -> Response:
        """Handle incoming message from Teams."""
        # Verify request has JSON body
        if req.content_type != "application/json":
            logger.warning(f"[{self.bot_id}] Invalid content type: {req.content_type}")
            return Response(status=415, text="Content-Type must be application/json")

        # Parse activity from request
        body = await req.json()
        activity = Activity().deserialize(body)

        # Get auth header
        auth_header = req.headers.get("Authorization", "")

        # Process activity
        async def turn_callback(turn_context: TurnContext):
            await self.bot.on_turn(turn_context)

        try:
            await self.adapter.process_activity(activity, auth_header, turn_callback)
            logger.info(f"[{self.bot_id}] Processed activity: {activity.type}")
            return Response(status=200)
        except Exception as e:
            logger.error(f"[{self.bot_id}] Failed to process activity: {e}", exc_info=True)
            return Response(status=500, text=str(e))


async def create_app() -> web.Application:
    """Create and configure the aiohttp web application."""
    app = web.Application()

    # Get settings
    settings = get_settings()

    # Create bot endpoints for both bots
    nous_endpoint = BotEndpoint("nous_bot")
    claude_endpoint = BotEndpoint("claude_bot")

    # Add routes
    app.router.add_post("/api/messages/nous_bot", nous_endpoint.handle_message)
    app.router.add_post("/api/messages/claude_bot", claude_endpoint.handle_message)

    # Health check endpoint
    async def health_check(req: Request) -> Response:
        return Response(text="Chorus is running!", status=200)

    app.router.add_get("/health", health_check)

    logger.info(f"Application configured with routes:")
    logger.info(f"  - POST /api/messages/nous_bot")
    logger.info(f"  - POST /api/messages/claude_bot")
    logger.info(f"  - GET /health")

    return app


def main():
    """Run the application."""
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("Starting Chorus Bot System")
    logger.info("=" * 60)
    logger.info(f"Host: {settings.host}")
    logger.info(f"Port: {settings.port}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 60)

    # Create and run app
    web.run_app(
        create_app(),
        host=settings.host,
        port=settings.port,
        print=None,  # Disable aiohttp's startup message
    )


if __name__ == "__main__":
    main()
