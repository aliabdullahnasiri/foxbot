from decimal import Decimal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        str_strip_whitespace=True,
        hide_input_in_errors=True,
    )

    # Telegram
    TELEGRAM_API_ID: str = ""
    TELEGRAM_API_HASH: SecretStr = SecretStr("")
    TELEGRAM_CHANNEL: str = ""
    TELEGRAM_SESSION: str = Field(default="foxbot.session", min_length=1)

    # Redis and Celery
    REDIS_URL: SecretStr = SecretStr("redis://localhost:6379/0")
    CELERY_BROKER_URL: SecretStr = SecretStr("")

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=60, gt=0)

    # MetaTrader 5 demo account
    MT5_LOGIN: int | None = Field(default=None, gt=0)
    MT5_PASSWORD: SecretStr = SecretStr("")
    MT5_SERVER: str = ""
    MT5_SYMBOL: str = "XAUUSD"
    MT5_MAGIC: int = 20261121

    # Trading limits and execution
    RISK_PERCENT: Decimal = Field(default=Decimal("0.5"), gt=0, le=Decimal("0.5"))
    MAX_DAILY_LOSS_PERCENT: Decimal = Field(default=Decimal(2), gt=0, le=2)
    MAX_ENTRY_DEVIATION: Decimal = Field(default=Decimal(2), ge=0)
    MAX_SPREAD: Decimal = Field(default=Decimal("0.5"), ge=0)
    MAX_SIGNAL_AGE_SECONDS: int = Field(default=120, gt=0)
    MAX_QUOTE_AGE_SECONDS: int = Field(default=10, gt=0)
    ENABLE_TRADING: bool = False

    # Local state and logging
    STATE_DB_PATH: str = "foxbot_state.sqlite3"
    LOG_LEVEL: str = "INFO"

    @field_validator("MT5_LOGIN", mode="before")
    @classmethod
    def empty_mt5_login_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


def get_settings() -> Settings:
    """Load current environment and local configuration when an operation starts."""
    return Settings()
