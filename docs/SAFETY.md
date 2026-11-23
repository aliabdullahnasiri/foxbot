# Safety and Risk Policy (hard rules)

Manual MT5 orders use an operator-supplied lot size on the connected terminal account. Account eligibility, real-mode opt-in, and portfolio risk controls described below apply only to the planned automated workflow. Manual submission requires explicit execution, a checked broker request, and a durable request ID.

**Default: demo mode and no execution.** This is an engineering test harness, not proof of profitable trading. Telegram provider win-rate claims are not verified.

1. Manual execution requires `--submit` and `ENABLE_TRADING=true`. The default command performs a dry run.
2. Verify the selected MT5 account mode and identity immediately before submission. Real orders also require `--mode real`, `ENABLE_REAL_TRADING=true`, and explicit credentials matching the connected account.
3. Restrict to XAUUSD on approved broker symbol; BUY/SELL only; attach SL and TP1 on entry.
4. Limit planned loss for each order to 0.5% of current equity. Include estimated fees and slippage. Reject the order if the planned loss exceeds the cap or cannot be verified.
5. No martingale, grid, averaging down, or position stacking. At most one FoxBot XAUUSD position.
6. For Telegram signals, the source message and Ollama JSON must agree exactly on symbol, side and numeric fields. No invented or missing prices.
7. SELL SL must be greater than entry and TP1 less; BUY SL must be less than entry and TP1 greater. All TP values must be correctly oriented.
8. Apply max signal age, quote freshness, spread and price-deviation thresholds; skip when violated. Prices thresholds measured in XAUUSD price units, not pips.
9. Price sizing from MT5 `order_calc_profit` and broker lot step; round **down**. If min volume risks too much, skip. Reject when contract data/order checks are missing or inconsistent.
10. Verify margin and trade permissions; never blindly retry an uncertain order submission. Preserve idempotency over restarts.
11. Credentials, Telegram session and trading records stay local and gitignored.
12. Fail closed for connectivity, parser, database, MT5, and configuration errors.

## Guardrail testing
Create unit tests for real-account opt-in and account-mode mismatch, missing SL, reversed levels, wrong symbol, duplicate message, price drift, per-order risk, min-lot risk, stale data, execution-disabled flag, and uncertain order result.
