# Convert a test signal to JSON

Start Ollama locally and download the model.

```sh
ollama pull qwen2.5:3b
```

From the FoxBot repository root, run `uv run python` and paste the following.
The client uses `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
`OLLAMA_TIMEOUT_SECONDS` from the project settings.

```python
import asyncio
from bot.core.ollama import extract_signal_json

signal = """NEW TRADE IDEA

XAUUSD SELL 3523

TP 1 3519
TP 2 3518
TP 3 3500

SL @ 3540"""

print(asyncio.run(extract_signal_json(signal)))
```

Expected JSON

```json
{
  "symbol": "XAUUSD",
  "side": "SELL",
  "entry_price": 3523,
  "stop_loss": 3540,
  "take_profits": [3519, 3518, 3500]
}
```

Compare every extracted value against the source message. The command only
prints the model output. FoxBot treats it as untrusted until source verification
and domain validation are implemented.

[Ollama chat API](https://docs.ollama.com/api/chat)
