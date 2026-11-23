# Test Plan

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution, a checked broker request, and a durable request ID.

Use `uv run pytest` with mocked Telethon, Ollama, and MT5; tests should not require real credentials, internet, or installed terminal.

## Parser
- Correct SELL and BUY extraction.
- Multi-TP extraction, use TP1 for order.
- Missing/duplicate/contradictory SL, invalid levels, unknown symbol.
- JSON malformed, timeout, unavailable Ollama, numeric hallucination/number missing from source.
- BUY vs SELL geometry tests.

## Telegram and state
- Only configured channel; only new messages.
- Repeated channel/message pair is ignored even after process restart.
- Order retry after uncertain MT5 response is **not** automatic.
- Edited/historical messages cannot trigger execution.

## MT5 and risk
- Trading disabled means no `order_send` call.
- Real submission requires explicit opt-in and matching configured credentials. Account-mode mismatches are rejected.
- Broker suffix supported via configured symbol.
- Correct side-specific quote (BUY ask / SELL bid).
- Market price outside allowed tolerance rejected.
- An existing FoxBot position, missing SL/TP, a stale quote, excessive spread, or insufficient margin blocks submission.
- `order_calc_profit()` used for stop-loss sizing; volume steps floor; minimum lot rejected if oversized.
- `order_check` failure blocks `order_send`; uncertain result requires reconciliation.

## Verification commands
```bash
uv sync
uv run ruff check .
uv run pytest -q
```
Never state tests pass unless they were run.
