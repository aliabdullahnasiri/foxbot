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

    # Celery broker
    CELERY_BROKER_URL: SecretStr = SecretStr("")

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=60, gt=0)

    # MetaTrader 5 account
    MT5_LOGIN: int | None = Field(default=None, gt=0)
    MT5_PASSWORD: SecretStr = SecretStr("")
    MT5_SERVER: str = ""
    MT5_SYMBOL: str = "XAUUSD"
    MT5_MAGIC: int = 20261121
    MT5_QUOTE_UTC_OFFSET_MINUTES: int = Field(default=0, ge=-840, le=840)

    # Trading limits and execution
    RISK_PERCENT: Decimal = Field(default=Decimal("0.5"), gt=0, le=Decimal("0.5"))
    MAX_ENTRY_DEVIATION: Decimal = Field(default=Decimal(2), ge=0)
    MAX_SPREAD: Decimal = Field(default=Decimal("0.5"), ge=0)
    MAX_SIGNAL_AGE_SECONDS: int = Field(default=120, gt=0)
    MAX_QUOTE_AGE_SECONDS: int = Field(default=10, gt=0)
    ENABLE_TRADING: bool = False
    ENABLE_REAL_TRADING: bool = False
    MT5_SLIPPAGE_ALLOWANCE: Decimal | None = Field(default=None, gt=0)
    MT5_ROUND_TRIP_COST_PER_LOT: Decimal | None = Field(default=None, ge=0)

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def mt5_quote_utc_offset_seconds(self) -> int:
        """Return the configured broker clock offset in seconds."""
        return self.MT5_QUOTE_UTC_OFFSET_MINUTES * 60

    @field_validator("MT5_LOGIN", mode="before")
    @classmethod
    def empty_mt5_login_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


def get_settings() -> Settings:
    """Load current environment and local configuration when an operation starts."""
    return Settings()
