from typing import TYPE_CHECKING, cast

from telethon import TelegramClient, types

from bot.core import config

if TYPE_CHECKING:
    from collections.abc import Awaitable


def positive_int(name: str, value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return number


def create_client() -> TelegramClient:
    settings = config.settings
    api_id = positive_int("TELEGRAM_API_ID", settings.TELEGRAM_API_ID)
    api_hash = settings.TELEGRAM_API_HASH.get_secret_value().strip()
    session = settings.TELEGRAM_SESSION
    if not api_hash or not session:
        raise ValueError("TELEGRAM_API_HASH and TELEGRAM_SESSION must be set.")
    return TelegramClient(session, api_id, api_hash, catch_up=False)


async def sign_in() -> None:
    """Create the user session interactively before starting the monitor."""
    # These Telethon methods return awaitables inside a running event loop.
    client = create_client()
    try:
        await cast("Awaitable[TelegramClient]", client.start())
        user = await client.get_me()
        if not isinstance(user, types.User) or user.bot:
            raise ValueError("Configure a Telegram user session.")
    finally:
        await cast("Awaitable[None]", client.disconnect())
