"""Discord application runner for Chorus bots."""

import asyncio
import logging
from src.config import get_settings, get_discord_bot_configs
from src.discord_bot import ChorusDiscordBot

logger = logging.getLogger(__name__)


async def run_bot(bot: ChorusDiscordBot, token: str):
    """Run a single Discord bot.

    Args:
        bot: Discord bot instance
        token: Bot token
    """
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error running bot {bot.config.name}: {e}", exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()


async def main():
    """Main entry point for Discord bots."""
    settings = get_settings()
    configs = get_discord_bot_configs(settings)

    logger.info("Starting Chorus Discord bots...")

    # Create bot instances
    bots = []
    for bot_id, config in configs.items():
        if config.discord_token:
            bot = ChorusDiscordBot(config)
            bots.append((bot, config.discord_token))
            logger.info(f"Created bot: {config.name} (bot_id: {bot_id})")
        else:
            logger.warning(f"Skipping {bot_id} - no Discord token configured")

    if not bots:
        logger.error("No Discord bots configured! Please set DISCORD_NOUS_TOKEN and/or DISCORD_CLAUDE_TOKEN in .env")
        return

    # Run all bots concurrently
    tasks = [run_bot(bot, token) for bot, token in bots]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down Discord bots...")
        for bot, _ in bots:
            if not bot.is_closed():
                await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
