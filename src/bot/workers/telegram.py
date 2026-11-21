import re
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import cast

from telethon import events, types, utils

from bot.core import config
from bot.core.logger import logger
from bot.core.ollama import OllamaError, extract_signal_json
from bot.core.telegram import create_client
from bot.workers.base import BaseWorker

SYMBOL = re.compile(r"\bXAUUSD\b", re.IGNORECASE)
SIDE = re.compile(r"\b(?:BUY|SELL)\b", re.IGNORECASE)


class TelegramMonitorWorker(BaseWorker):
    name = "telegram.monitor"
    ignore_result = True

    async def _run(self) -> None:
        settings = config.settings
        channel = settings.TELEGRAM_CHANNEL
        if not channel:
            raise ValueError("TELEGRAM_CHANNEL must identify one Telegram channel.")
        max_age = timedelta(seconds=settings.MAX_SIGNAL_AGE_SECONDS)
        target = types.PeerChannel(int(channel)) if channel.isdecimal() else channel
        client = create_client()

        try:
            await client.connect()
            user = await client.get_me()
            if user is None:
                raise ValueError(
                    "Telegram session is unauthorized. Run uv run bot telegram-login."
                )
            if not isinstance(user, types.User) or user.bot:
                raise ValueError("Configure a Telegram user session.")
            try:
                entity = await client.get_entity(target)
            except ValueError:
                if not channel.removeprefix("-").isdecimal():
                    raise ValueError(
                        "TELEGRAM_CHANNEL could not be resolved."
                    ) from None
                # A fresh session may not have cached the access hash for a private channel.
                target_id = int(channel)
                if target_id > 0:
                    target_id = utils.get_peer_id(types.PeerChannel(target_id))
                entity = None
                async for dialog in client.iter_dialogs():
                    if dialog.id == target_id:
                        entity = dialog.entity
                        break
            if (
                not isinstance(entity, types.Channel)
                or not entity.broadcast
                or entity.left
            ):
                raise ValueError(
                    "TELEGRAM_CHANNEL must be a broadcast channel you joined."
                )

            channel_id = utils.get_peer_id(entity)
            started_at = datetime.now(UTC)

            @client.on(events.NewMessage(chats=channel_id))
            async def on_message(event: events.NewMessage.Event) -> None:
                now = datetime.now(UTC)
                if event.chat_id != channel_id or not started_at < event.date <= now:
                    return
                if now - event.date > max_age:
                    return
                text = event.raw_text or ""

                if SYMBOL.search(text) and SIDE.search(text):
                    logger.info(
                        "Telegram signal candidate channel_id=%s message_id=%s",
                        channel_id,
                        event.id,
                    )

                    try:
                        signal = await extract_signal_json(text)
                    except OllamaError as exc:
                        logger.warning("Skipping message_id=%s: %s", event.id, exc)
                        return
                    logger.info("Unverified signal extraction: %s", signal)

            logger.info("Monitoring Telegram channel_id=%s", channel_id)

            await cast(Awaitable[None], client.run_until_disconnected())
        finally:
            await cast(Awaitable[None], client.disconnect())
