"""Configuration management for Chorus bot system."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # OpenRouter API
    openrouter_api_key: str = Field(..., description="OpenRouter API key")

    # Tavily Search API
    tavily_api_key: str = Field(default="", description="Tavily API key for web search")

    # Azure Bot Service credentials - Nous Bot
    nous_bot_app_id: str = Field(..., description="Azure App ID for Nous bot")
    nous_bot_app_password: str = Field(..., description="Azure App Password for Nous bot")

    # Azure Bot Service credentials - Claude Bot
    claude_bot_app_id: str = Field(..., description="Azure App ID for Claude bot")
    claude_bot_app_password: str = Field(..., description="Azure App Password for Claude bot")

    # Discord Bot tokens
    discord_nous_token: str = Field(default="", description="Discord token for Nous bot")
    discord_claude_token: str = Field(default="", description="Discord token for Claude bot")

    # Server configuration
    port: int = Field(default=3978, description="Server port")
    host: str = Field(default="0.0.0.0", description="Server host")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Bot selection
    active_bots: str = Field(default="", description="Comma-separated list of bots to load (e.g., 'nous,claude')")


class BotConfig:
    """Configuration for a single bot instance."""

    def __init__(
        self,
        bot_id: str,
        name: str,
        model: str,
        system_prompt: str,
        app_id: str = "",
        app_password: str = "",
        discord_token: str = "",
        # Context configuration
        max_messages: int = 10,
        max_verbatim_messages: int = 30,
        max_decision_context: int = 5,
        max_tokens_response: int = 500,
        max_tokens_decision: int = 10,
        # Tool calling
        enable_tools: bool = False,
        # Vision capability
        supports_vision: bool = False,
    ):
        self.bot_id = bot_id
        self.app_id = app_id
        self.app_password = app_password
        self.discord_token = discord_token
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.memory_db_path = f"data/memories/{bot_id}.db"

        # Context limits
        self.max_messages = max_messages
        self.max_verbatim_messages = max_verbatim_messages
        self.max_decision_context = max_decision_context
        self.max_tokens_response = max_tokens_response
        self.max_tokens_decision = max_tokens_decision

        # Tool calling
        self.enable_tools = enable_tools

        # Vision capability
        self.supports_vision = supports_vision


class BotLoader:
    """Loads bot configurations from directory-based bot packages."""

    def __init__(self, bots_dir: str = "bots", settings: Settings = None):
        """Initialize bot loader.

        Args:
            bots_dir: Directory containing bot packages
            settings: Application settings for resolving env vars
        """
        self.bots_dir = Path(bots_dir)
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(__name__)

    def load_bots(self, active_bots: Optional[List[str]] = None) -> Dict[str, BotConfig]:
        """Load bot configurations from directory.

        Args:
            active_bots: List of bot names to load. If None, loads all bots.

        Returns:
            Dictionary mapping bot_id to BotConfig
        """
        if not self.bots_dir.exists():
            self.logger.warning(f"Bots directory not found: {self.bots_dir}")
            return {}

        configs = {}

        # Get list of bot directories (skip those starting with _)
        bot_dirs = [d for d in self.bots_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

        for bot_dir in bot_dirs:
            bot_name = bot_dir.name

            # Filter by active_bots if specified
            if active_bots is not None and bot_name not in active_bots:
                self.logger.info(f"Skipping bot '{bot_name}' (not in ACTIVE_BOTS)")
                continue

            try:
                config = self._load_bot_config(bot_dir)
                if config:
                    configs[config.bot_id] = config
                    self.logger.info(f"Loaded bot configuration: {bot_name} ({config.bot_id})")
            except Exception as e:
                self.logger.error(f"Error loading bot '{bot_name}': {e}", exc_info=True)

        # Warn about any active_bots that weren't found
        if active_bots:
            loaded_names = {Path(d).name for d in bot_dirs}
            for bot_name in active_bots:
                if bot_name not in loaded_names:
                    self.logger.warning(f"Active bot '{bot_name}' not found in {self.bots_dir}")

        return configs

    def _load_bot_config(self, bot_dir: Path) -> Optional[BotConfig]:
        """Load configuration for a single bot.

        Args:
            bot_dir: Path to bot directory

        Returns:
            BotConfig instance or None if loading failed
        """
        config_file = bot_dir / "config.json"
        prompt_file = bot_dir / "prompt.txt"

        # Check required files exist
        if not config_file.exists():
            self.logger.error(f"Missing config.json in {bot_dir}")
            return None

        if not prompt_file.exists():
            self.logger.error(f"Missing prompt.txt in {bot_dir}")
            return None

        # Load config JSON
        with open(config_file, "r") as f:
            config_data = json.load(f)

        # Load prompt
        with open(prompt_file, "r") as f:
            system_prompt = f.read().strip()

        # Resolve environment variables for credentials
        # Try to get from Settings object first (loaded from .env by pydantic)
        # Fall back to os.getenv for actual environment variables
        discord_token_env = config_data.get("discord_token_env", "")
        app_id_env = config_data.get("app_id_env", "")
        app_password_env = config_data.get("app_password_env", "")

        # Map env var names to Settings attributes
        discord_token = ""
        if discord_token_env:
            # Try Settings object first
            discord_token = getattr(self.settings, discord_token_env.lower(), "")
            # Fall back to os.getenv
            if not discord_token:
                discord_token = os.getenv(discord_token_env, "")

        app_id = ""
        if app_id_env:
            app_id = getattr(self.settings, app_id_env.lower(), "")
            if not app_id:
                app_id = os.getenv(app_id_env, "")

        app_password = ""
        if app_password_env:
            app_password = getattr(self.settings, app_password_env.lower(), "")
            if not app_password:
                app_password = os.getenv(app_password_env, "")

        # Create BotConfig instance
        bot_config = BotConfig(
            bot_id=config_data.get("bot_id"),
            name=config_data.get("name"),
            model=config_data.get("model"),
            system_prompt=system_prompt,
            app_id=app_id,
            app_password=app_password,
            discord_token=discord_token,
            max_messages=config_data.get("max_messages", 10),
            max_verbatim_messages=config_data.get("max_verbatim_messages", 30),
            max_decision_context=config_data.get("max_decision_context", 5),
            max_tokens_response=config_data.get("max_tokens_response", 500),
            max_tokens_decision=config_data.get("max_tokens_decision", 10),
            enable_tools=config_data.get("enable_tools", False),
            supports_vision=config_data.get("supports_vision", False),
        )

        return bot_config


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from some verbose libraries
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_bot_configs(settings: Settings) -> Dict[str, BotConfig]:
    """Create bot configurations for Teams from settings."""

    configs = {
        "nous_bot": BotConfig(
            bot_id="nous_bot",
            name="Nous",
            model="nousresearch/hermes-4-405b",
            system_prompt=(
                "You are Nous, an AI assistant participating in a chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be helpful, engaging, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate. "
                "\n\n"
                "IMPORTANT: You have access to web search via Tavily. When asked about:\n"
                "- Current events, news, or headlines\n"
                "- Today's weather or real-time conditions\n"
                "- Recent developments or breaking news\n"
                "- Up-to-date facts or statistics\n"
                "- Any information that changes frequently\n"
                "You SHOULD use the web_search tool to get accurate, current information."
            ),
            app_id=settings.nous_bot_app_id,
            app_password=settings.nous_bot_app_password,
            # Hermes-4 has large context - can handle extended history
            max_messages=40,
            max_decision_context=10,
            max_tokens_response=800,
            max_tokens_decision=10,
            enable_tools=True,
        ),
        "claude_bot": BotConfig(
            bot_id="claude_bot",
            name="Claude",
            model="anthropic/claude-sonnet-4.5",
            system_prompt=(
                "You are Claude, an AI assistant participating in a chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be thoughtful, helpful, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate. "
                "You have access to web search via Tavily - use it when you need current information "
                "or facts that might have changed since your training data."
            ),
            app_id=settings.claude_bot_app_id,
            app_password=settings.claude_bot_app_password,
            # Claude has 200k context - can handle more history
            max_messages=50,
            max_decision_context=10,
            max_tokens_response=1000,
            max_tokens_decision=10,
            # Enable tool calling for web search
            enable_tools=True,
        ),
    }

    return configs


def get_discord_bot_configs(settings: Settings) -> Dict[str, BotConfig]:
    """Create bot configurations for Discord from settings.

    First tries to load from bots/ directory. If that fails or directory
    doesn't exist, falls back to hardcoded configurations.
    """

    # Try loading from bots/ directory first
    loader = BotLoader(bots_dir="bots", settings=settings)

    # Parse ACTIVE_BOTS env var
    active_bots = None
    if settings.active_bots:
        active_bots = [name.strip() for name in settings.active_bots.split(",") if name.strip()]
        logging.getLogger(__name__).info(f"ACTIVE_BOTS specified: {active_bots}")

    # Try loading from directory
    configs = loader.load_bots(active_bots=active_bots)

    # If we successfully loaded configs OR bots directory exists, return them
    # (even if empty due to ACTIVE_BOTS filtering)
    if configs or loader.bots_dir.exists():
        logging.getLogger(__name__).info(f"Loaded {len(configs)} bot(s) from bots/ directory")
        return configs

    # Fall back to hardcoded configs only if bots directory doesn't exist
    logging.getLogger(__name__).warning("Bots directory not found - falling back to hardcoded bot configurations")

    configs = {
        "discord_nous": BotConfig(
            bot_id="discord_nous",
            name="Nous",
            model="nousresearch/hermes-4-405b",
            system_prompt=(
                "You are Nous, an AI assistant participating in a Discord chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be helpful, engaging, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate. "
                "\n\n"
                "IMAGE GENERATION: You can create images! Use the generate_image tool when:\n"
                "- Users explicitly ask you to draw, create, or generate an image\n"
                "- An image would help illustrate a concept or idea\n"
                "- Visual examples would enhance the conversation\n"
                "Be creative and descriptive with image prompts!"
                "\n\n"
                "IMPORTANT: You have access to web search via Tavily. When asked about:\n"
                "- Current events, news, or headlines\n"
                "- Today's weather or real-time conditions\n"
                "- Recent developments or breaking news\n"
                "- Up-to-date facts or statistics\n"
                "- Any information that changes frequently\n"
                "You SHOULD use the web_search tool to get accurate, current information."
                "\n\n"
                "Note: You cannot see images yourself, but your colleague Claude can! "
                "If someone posts an image, you might want to defer to Claude for visual analysis."
                "\n\n"
                "IMPORTANT: This is Discord - keep responses concise and conversational (typically 1-3 short paragraphs). "
                "Be brief by default, but don't sacrifice clarity. If a topic needs detail, you can be thorough - "
                "just stay focused and finish your thoughts cleanly. Make every word count."
            ),
            discord_token=settings.discord_nous_token,
            # Hermes-4 has large context - can handle extended history
            max_messages=40,
            max_decision_context=10,
            max_tokens_response=800,
            max_tokens_decision=10,
            enable_tools=True,
        ),
        "discord_claude": BotConfig(
            bot_id="discord_claude",
            name="Claude",
            model="anthropic/claude-sonnet-4.5",
            system_prompt=(
                "You are Claude, an AI assistant participating in a Discord chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be thoughtful, helpful, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate. "
                "\n\n"
                "VISION: You can see and analyze images shared in the chat. When users post images, "
                "you can describe what you see, answer questions about them, and provide insights. "
                "Be detailed and thoughtful in your image analysis."
                "\n\n"
                "IMAGE GENERATION: You can create images! Use the generate_image tool when:\n"
                "- Users explicitly ask you to draw, create, or generate an image\n"
                "- An image would help illustrate a concept or idea\n"
                "- Visual examples would enhance understanding\n"
                "Provide detailed, thoughtful prompts that capture the essence of what's needed."
                "\n\n"
                "You have access to web search via Tavily - use it when you need current information "
                "or facts that might have changed since your training data."
                "\n\n"
                "IMPORTANT: This is Discord - keep responses concise and conversational (typically 1-3 short paragraphs). "
                "Be brief by default, but don't sacrifice clarity. If a topic needs detail, you can be thorough - "
                "just stay focused and finish your thoughts cleanly. Make every word count."
            ),
            discord_token=settings.discord_claude_token,
            # Claude has 200k context - can handle more history
            max_messages=50,
            max_decision_context=10,
            max_tokens_response=1000,
            max_tokens_decision=10,
            # Enable tool calling for web search and image generation
            enable_tools=True,
            # Claude supports vision
            supports_vision=True,
        ),
    }

    return configs


# Global settings instance (loaded lazily)
_settings: Settings | None = None
_bot_configs: Dict[str, BotConfig] | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        setup_logging(_settings.log_level)
    return _settings


def get_all_bot_configs() -> Dict[str, BotConfig]:
    """Get or create all bot configurations."""
    global _bot_configs
    if _bot_configs is None:
        settings = get_settings()
        _bot_configs = get_bot_configs(settings)
    return _bot_configs


def get_bot_config(bot_id: str) -> BotConfig:
    """Get a specific bot configuration by ID."""
    configs = get_all_bot_configs()
    if bot_id not in configs:
        raise ValueError(f"Unknown bot_id: {bot_id}")
    return configs[bot_id]
