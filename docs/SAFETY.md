# Safety and Risk Policy (hard rules)

**Demo only. Default: no execution.** This is an engineering test harness, not proof of profitable trading. Telegram provider win-rate claims are not verified.

1. Trade execution requires `ENABLE_TRADING=true`; otherwise log dry-run only.
2. Inspect MT5 account mode every time an order may be sent. If demo status cannot be verified, **reject**; never support live accounts in v1.
3. Restrict to XAUUSD on approved broker symbol; BUY/SELL only; attach SL and TP1 on entry.
4. Respect 0.5% of current equity maximum planned risk per signal, and 2% of opening daily equity daily-loss cap. Include known realized P&L and conservative floating drawdown when enforcing the cap. Treat cap breach/uncertain data as no-trade.
5. No martingale, grid, averaging down, or position stacking. At most one FoxBot XAUUSD position.
6. Source message and Ollama JSON must agree exactly on symbol, side and numeric fields. No invented or missing prices.
7. SELL SL must be greater than entry and TP1 less; BUY SL must be less than entry and TP1 greater. All TP values must be correctly oriented.
8. Apply max signal age, quote freshness, spread and price-deviation thresholds; skip when violated. Prices thresholds measured in XAUUSD price units, not pips.
9. Price sizing from MT5 `order_calc_profit` and broker lot step; round **down**. If min volume risks too much, skip. Reject when contract data/order checks are missing or inconsistent.
10. Verify margin and trade permissions; never blindly retry an uncertain order submission. Preserve idempotency over restarts.
11. Credentials, Telegram session and trading records stay local and gitignored.
12. Fail closed for connectivity, parser, database, MT5, and configuration errors.

## Guardrail testing
Create unit tests for real-account rejection, missing SL, reversed levels, wrong symbol, duplicate message, price drift, daily-loss cap, min-lot risk, stale data, execution-disabled flag, and uncertain order result.
