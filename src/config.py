"""Central configuration loaded from .env file."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///data/247sales.db"

    # Twitter API
    TWITTER_BEARER_TOKEN: str = ""
    NITTER_INSTANCES: list[str] = Field(default=["nitter.net", "nitter.privacydev.net"])

    # Email notifications
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_TO: str = ""  # comma-separated list

    # Slack
    SLACK_WEBHOOK_URL: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Scheduling
    AI_TRENDS_CRON: str = "0 */2 * * *"
    TWITTER_SEO_CRON: str = "*/15 * * * *"
    DIGEST_CRON: str = "0 8 * * *"
    TIMEZONE: str = "UTC"

    # Summarization
    SUMMARIZER_MODE: str = "extractive"  # "extractive" or "llm"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Scraping
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = "247sales-bot/0.1"

    @property
    def smtp_recipients(self) -> list[str]:
        return [e.strip() for e in self.SMTP_TO.split(",") if e.strip()]

    @property
    def email_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_TO)

    @property
    def slack_configured(self) -> bool:
        return bool(self.SLACK_WEBHOOK_URL)

    @property
    def telegram_configured(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)

    @property
    def twitter_configured(self) -> bool:
        return bool(self.TWITTER_BEARER_TOKEN)
