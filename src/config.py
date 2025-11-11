"""Configuration management for Chorus bot system."""

import logging
from typing import Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Azure Bot Service credentials - Nous Bot
    nous_bot_app_id: str = Field(..., description="Azure App ID for Nous bot")
    nous_bot_app_password: str = Field(..., description="Azure App Password for Nous bot")

    # Azure Bot Service credentials - Claude Bot
    claude_bot_app_id: str = Field(..., description="Azure App ID for Claude bot")
    claude_bot_app_password: str = Field(..., description="Azure App Password for Claude bot")

    # Server configuration
    port: int = Field(default=3978, description="Server port")
    host: str = Field(default="0.0.0.0", description="Server host")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


class BotConfig:
    """Configuration for a single bot instance."""

    def __init__(
        self,
        bot_id: str,
        app_id: str,
        app_password: str,
        name: str,
        model: str,
        system_prompt: str,
    ):
        self.bot_id = bot_id
        self.app_id = app_id
        self.app_password = app_password
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.memory_db_path = f"data/memories/{bot_id}.db"


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
    """Create bot configurations from settings."""

    configs = {
        "nous_bot": BotConfig(
            bot_id="nous_bot",
            app_id=settings.nous_bot_app_id,
            app_password=settings.nous_bot_app_password,
            name="Nous",
            model="nousresearch/hermes-4-405b",
            system_prompt=(
                "You are Nous, an AI assistant participating in a Microsoft Teams chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be helpful, engaging, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate."
            ),
        ),
        "claude_bot": BotConfig(
            bot_id="claude_bot",
            app_id=settings.claude_bot_app_id,
            app_password=settings.claude_bot_app_password,
            name="Claude",
            model="anthropic/claude-sonnet-4.5",
            system_prompt=(
                "You are Claude, an AI assistant participating in a Microsoft Teams chat. "
                "You can interact naturally with humans and other AI bots in the conversation. "
                "Be thoughtful, helpful, and conversational. You don't need to respond to every "
                "message - only when you have something valuable to contribute. You can also "
                "react to messages with emoji when appropriate."
            ),
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
