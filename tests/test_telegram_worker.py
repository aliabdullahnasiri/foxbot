import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from telethon import events, types, utils

from bot.core import config
from bot.core.celery import celery_app
from bot.core.ollama import OllamaError
from bot.core.settings import Settings
from bot.workers.telegram import TelegramMonitorWorker


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_CHANNEL", "@signals")
    monkeypatch.setenv("MAX_SIGNAL_AGE_SECONDS", "120")
    monkeypatch.setattr(config, "settings", Settings())
    fake = Mock()
    fake.connect = AsyncMock()
    fake.disconnect = AsyncMock()
    fake.get_me = AsyncMock(return_value=types.User(id=1, bot=False))
    fake.get_entity = AsyncMock(
        return_value=types.Channel(
            id=42,
            title="Signals",
            photo=types.ChatPhotoEmpty(),
            date=None,
            broadcast=True,
        )
    )
    fake.run_until_disconnected = AsyncMock()
    monkeypatch.setattr("bot.workers.telegram.create_client", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_monitor_logs_only_fresh_candidates(client, caplog, monkeypatch):
    channel_id = utils.get_peer_id(client.get_entity.return_value)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    now = start + timedelta(minutes=3)
    clock = Mock()
    clock.now.side_effect = [start] + [now] * 6
    monkeypatch.setattr("bot.workers.telegram.datetime", clock)
    caplog.set_level(logging.INFO)
    extract = AsyncMock(
        side_effect=OllamaError("Ollama output failed signal validation.")
    )
    monkeypatch.setattr("bot.workers.telegram.extract_signal_json", extract)

    async def dispatch():
        builder = client.on.call_args.args[0]
        assert isinstance(builder, events.NewMessage)
        assert builder.chats == channel_id
        assert builder.incoming is None and builder.outgoing is None
        for outgoing in (False, True):
            assert (
                builder.build(
                    types.UpdateNewChannelMessage(
                        message=types.Message(
                            id=1,
                            peer_id=types.PeerChannel(42),
                            date=now,
                            message="XAUUSD SELL 3500",
                            out=outgoing,
                        ),
                        pts=1,
                        pts_count=1,
                    )
                )
                is not None
            )
        handler = client.on.return_value.call_args.args[0]
        for message_id, chat, text, date in [
            (1, channel_id, "XAUUSD SELL 3500", now),
            (2, channel_id - 1, "XAUUSD BUY 3500", now),
            (3, channel_id, "XAUUSD BUY 3500", start),
            (4, channel_id, "XAUUSD BUY 3500", start + timedelta(seconds=1)),
            (5, channel_id, "Good morning", now),
            (6, channel_id, "XAUUSD BUY 3500", now + timedelta(seconds=1)),
        ]:
            await handler(
                SimpleNamespace(id=message_id, chat_id=chat, raw_text=text, date=date)
            )

    client.run_until_disconnected.side_effect = dispatch
    await TelegramMonitorWorker()._run()
    extract.assert_awaited_once_with("XAUUSD SELL 3500")
    assert "Skipping message_id=1" in caplog.text
    candidates = [
        record.message for record in caplog.records if "candidate" in record.message
    ]
    assert candidates == [
        f"Telegram signal candidate channel_id={channel_id} message_id=1"
    ]
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_monitor_rejects_unauthorized_session(client):
    client.get_me.return_value = None
    with pytest.raises(ValueError, match="session is unauthorized"):
        await TelegramMonitorWorker()._run()
    client.on.assert_not_called()
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_monitor_disconnects_after_connection_failure(client):
    client.run_until_disconnected.side_effect = ConnectionError("connection lost")
    with pytest.raises(ConnectionError, match="connection lost"):
        await TelegramMonitorWorker()._run()
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_monitor_finds_private_channel_by_id(client, monkeypatch):
    entity = client.get_entity.return_value
    channel_id = utils.get_peer_id(entity)
    monkeypatch.setattr(config.settings, "TELEGRAM_CHANNEL", str(channel_id))
    client.get_entity.side_effect = ValueError()

    async def dialogs():
        yield SimpleNamespace(id=channel_id, entity=entity)

    client.iter_dialogs.side_effect = dialogs
    await TelegramMonitorWorker()._run()
    client.on.assert_called_once()
    client.disconnect.assert_awaited_once()


def test_registered_celery_task_runs_async_monitor(client):
    task = celery_app.tasks["telegram.monitor"]
    assert isinstance(task, TelegramMonitorWorker)
    assert task.apply(throw=True).successful()
    client.run_until_disconnected.assert_awaited_once()
