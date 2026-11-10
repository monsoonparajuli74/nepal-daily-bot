"""Application configuration, loaded entirely from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NPT_OFFSET_MINUTES = 5 * 60 + 45  # UTC+5:45


class Settings(BaseSettings):
    """Runtime settings. Every value can be overridden with an env var of the same name."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Telegram Bot API ----
    telegram_bot_token: str = ""
    #: Secret echoed back by Telegram in X-Telegram-Bot-Api-Secret-Token.
    telegram_webhook_secret: str = ""
    #: "webhook" (production default) or "polling" (local dev, no public URL needed).
    telegram_mode: str = "webhook"
    #: Bot username (without the leading @). Used for t.me share/deep links.
    bot_username: str = ""
    telegram_max_connections: int = 40
    telegram_drop_pending_updates: bool = True
    telegram_poll_timeout: int = 30
    #: Publish commands/descriptions and (un)set the webhook at startup. Disable in tests.
    telegram_setup_on_startup: bool = True
    public_base_url: str = ""
    bot_sender_name: str = "Sajilo Nepal"

    # ---- Database ----
    database_url: str = "sqlite+aiosqlite:///./everyday_nepal.db"
    auto_create_tables: bool = True

    # ---- App ----
    environment: str = "development"
    log_level: str = "INFO"
    scheduler_enabled: bool = True
    refresh_on_startup: bool = True
    rate_limit_per_minute: int = 20
    group_rate_limit_per_minute: int = 6
    unsupported_reply_cooldown_seconds: int = 60
    dedupe_ttl_hours: int = 24
    http_timeout_seconds: float = 10.0
    max_text_length: int = 4096
    user_data_retention_days: int = 30
    welcome_after_silence_days: int = 30
    analytics_salt: str = "change-this-salt"

    # ---- Daily briefing ----
    feature_daily_digest: bool = False
    digest_time_npt: str = "07:00"
    digest_rate_per_second: int = 20

    # Scheduled source refresh times use Nepal Time (NPT).
    refresh_forex_seconds: int = 3600
    refresh_metals_seconds: int = 3600
    refresh_fuel_seconds: int = 21600
    refresh_vegetables_seconds: int = 10800
    refresh_weather_seconds: int = 1800
    refresh_news_hours: int = Field(default=2, ge=1, le=12)
    refresh_forex_hour_npt: int = Field(default=11, ge=0, le=23)
    refresh_forex_minute_npt: int = Field(default=15, ge=0, le=59)
    refresh_metals_hour_npt: int = Field(default=10, ge=0, le=23)
    refresh_metals_minute_npt: int = Field(default=30, ge=0, le=59)
    refresh_fuel_hour_npt: int = Field(default=6, ge=0, le=23)
    refresh_fuel_minute_npt: int = Field(default=0, ge=0, le=59)
    refresh_vegetables_hour_npt: int = Field(default=5, ge=0, le=23)
    refresh_vegetables_minute_npt: int = Field(default=30, ge=0, le=59)
    horoscope_hour_npt: int = 5

    # Data files
    data_dir: str = "app/data"

    # Derived / quoting
    user_agent: str = "SajiloNepalBot/1.0 (+https://github.com)"

    @field_validator("public_base_url")
    @classmethod
    def _strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("bot_username")
    @classmethod
    def _strip_username(cls, value: str) -> str:
        return value.strip().lstrip("@")

    @field_validator("telegram_mode")
    @classmethod
    def _normalise_mode(cls, value: str) -> str:
        value = (value or "").strip().lower()
        return value if value in {"webhook", "polling"} else "webhook"

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url}/telegram/webhook" if self.public_base_url else ""

    @property
    def bot_link(self) -> str:
        return f"https://t.me/{self.bot_username}" if self.bot_username else ""

    @property
    def start_link(self) -> str:
        return self.bot_link

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def static_dir(self) -> str:
        return self.data_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
