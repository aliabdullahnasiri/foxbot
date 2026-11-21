import json
from functools import partial

import httpx
import pytest

from bot.core.ollama import OllamaError, extract_signal_json


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ['{"entry_price": 3523.00}', "invalid", "[]"])
async def test_extract_signal_json(monkeypatch, content):
    signal = "XAUUSD SELL 3523.00"

    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["format"] == "json"
        assert payload["stream"] is False
        assert payload["messages"][-1] == {"role": "user", "content": signal}
        return httpx.Response(200, json={"message": {"content": content}})

    client = partial(httpx.AsyncClient, transport=httpx.MockTransport(respond))
    monkeypatch.setattr("bot.core.ollama.httpx.AsyncClient", client)
    if content.startswith("{"):
        assert await extract_signal_json(signal) == content
    else:
        with pytest.raises(OllamaError, match="valid JSON object"):
            await extract_signal_json(signal)
