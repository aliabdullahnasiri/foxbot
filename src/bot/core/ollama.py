import json
from decimal import Decimal
from importlib.resources import files
from typing import Never

import httpx
from pydantic import ValidationError

from bot.core.config import settings
from bot.schemas.signal.data.signal import SignalData

SIGNAL_PROMPT = files("bot.prompts").joinpath("signal.md")


class OllamaError(RuntimeError):
    """Ollama could not return a valid signal."""


def _reject_constant(value: str) -> Never:
    raise ValueError(f"Invalid JSON constant {value}")


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return fields


async def extract_signal_json(message: str) -> str:
    """Return the model's untrusted JSON text without re-encoding prices."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {
                "role": "system",
                "content": SIGNAL_PROMPT.read_text(encoding="utf-8").strip(),
            },
            {"role": "user", "content": message},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise OllamaError("Ollama request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaError(f"Ollama returned HTTP {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        raise OllamaError("Could not reach Ollama.") from exc

    try:
        content = response.json()["message"]["content"]
        if isinstance(content, str):
            result = json.loads(
                content,
                parse_float=Decimal,
                parse_int=Decimal,
                parse_constant=_reject_constant,
                object_pairs_hook=_unique_fields,
            )
            if isinstance(result, dict):
                SignalData.model_validate(result)
                return content
    except ValidationError as exc:
        raise OllamaError("Ollama output failed signal validation.") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise OllamaError("Ollama did not return a valid JSON object.") from exc
    raise OllamaError("Ollama did not return a valid JSON object.")
