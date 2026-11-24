"""Synchronous MetaTrader 5 adapter for the mt5linux bridge."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from math import isfinite
from time import time
from types import TracebackType
from typing import Any, Literal, Self

from mt5linux import MetaTrader5

from bot.core.settings import Settings, get_settings
from bot.schemas.mt5.data.market_order import MarketOrder


class MT5ServiceError(RuntimeError):
    """MT5 connection, validation, or API failure."""


class MT5Service:
    """Connect to the selected account and use plain Python values across RPyC."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18812,
        *,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        magic: int = 123456,
        deviation: int = 20,
    ) -> None:
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.server = server
        self.magic = magic
        self.deviation = deviation
        self._client: MetaTrader5 | None = None

    @property
    def mt5(self) -> MetaTrader5:
        if self._client is None:
            raise MT5ServiceError("MT5 is not connected")
        return self._client

    def __enter__(self) -> Self:
        return self.connect()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.disconnect()

    def connect(self) -> Self:
        """Initialize the terminal, optionally log in, with the supplied credentials."""
        if self._client is not None:
            raise MT5ServiceError("Already connected")
        if self.login is None:
            if self.password is not None or self.server is not None:
                raise ValueError("Provide login, password, and server together")
        elif not self.password or not self.server:
            raise ValueError("Provide login, password, and server together")

        try:
            self._client = MetaTrader5(host=self.host, port=self.port)
            if not self.mt5.initialize():
                raise MT5ServiceError(f"MT5 initialization failed: {self.last_error()}")
            if self.login is not None and not self.mt5.login(
                self.login, password=self.password, server=self.server
            ):
                raise MT5ServiceError("MT5 login failed")
        except BaseException as exc:
            try:
                self.disconnect()
            except MT5ServiceError:
                exc.add_note("MT5 shutdown also failed during connection cleanup")
            if isinstance(exc, Exception) and not isinstance(exc, MT5ServiceError):
                raise MT5ServiceError("MT5 connection failed") from None
            raise
        return self

    def disconnect(self) -> None:
        """Shut down the terminal connection."""
        client = self._client
        self._client = None
        if client is not None:
            try:
                client.shutdown()
            except Exception as exc:
                raise MT5ServiceError("MT5 shutdown failed") from exc

    def _eval(self, expression: str) -> Any:
        client = self.mt5
        try:
            return client.eval(expression)
        except Exception as exc:
            raise MT5ServiceError("MT5 bridge call failed") from exc

    def last_error(self) -> tuple[int, str]:
        return self._eval("mt5.last_error()")

    def _record(self, expression: str, name: str) -> dict[str, Any]:
        result = self._eval(
            "(lambda row: dict(row._asdict()) if row is not None else None)"
            f"({expression})"
        )
        if result is None:
            raise MT5ServiceError(f"{name} failed: {self.last_error()}")
        return result

    def _records(self, expression: str, name: str) -> list[dict[str, Any]]:
        result = self._eval(
            "(lambda rows: [dict(row._asdict()) for row in rows] "
            "if rows is not None else None)"
            f"({expression})"
        )
        if result is None:
            raise MT5ServiceError(f"{name} failed: {self.last_error()}")
        return result

    def account(self) -> dict[str, Any]:
        return self._record("mt5.account_info()", "account_info")

    def symbol_info(self, symbol: str) -> dict[str, Any]:
        """Ensure the symbol exists and is selected in Market Watch."""
        quoted_symbol = str.__repr__(symbol)
        expression = f"mt5.symbol_info({quoted_symbol})"
        info = self._record(expression, "symbol_info")
        if not info.get("visible"):
            if not self._eval(f"mt5.symbol_select({quoted_symbol}, True)"):
                raise MT5ServiceError(f"Cannot enable symbol {quoted_symbol}")
            info = self._record(expression, "symbol_info")
            if not info.get("visible"):
                raise MT5ServiceError(f"Symbol {quoted_symbol} is still not visible")
        return info

    def tick(self, symbol: str) -> dict[str, Any]:
        self.symbol_info(symbol)
        tick = self._record(
            f"mt5.symbol_info_tick({str.__repr__(symbol)})", "symbol_info_tick"
        )
        bid, ask = tick.get("bid"), tick.get("ask")
        if (
            not isinstance(bid, (int, float))
            or not isinstance(ask, (int, float))
            or not isfinite(bid)
            or not isfinite(ask)
            or not 0 < bid <= ask
        ):
            raise MT5ServiceError(f"Invalid tick prices for {symbol}")
        return tick

    def positions(self, symbol: str, ticket: int | None = None) -> list[dict[str, Any]]:
        rows = self._records(f"mt5.positions_get(symbol={symbol!r})", "positions_get")
        return [
            row
            for row in rows
            if row["symbol"] == symbol and (ticket is None or row["ticket"] == ticket)
        ]

    def position_side(self, position_type: int) -> Literal["buy", "sell"]:
        if position_type == self.mt5.POSITION_TYPE_BUY:
            return "buy"
        if position_type == self.mt5.POSITION_TYPE_SELL:
            return "sell"
        raise MT5ServiceError("Unknown MT5 position type")

    def close_position(
        self, ticket: int, settings: Settings, *, submit: bool = False
    ) -> dict[str, Any]:
        self._validate_settings(settings)
        if submit and not settings.ENABLE_TRADING:
            raise MT5ServiceError("Order submission requires ENABLE_TRADING=true")
        symbol = settings.MT5_SYMBOL
        rows = self.positions(symbol, ticket)
        if len(rows) != 1:
            raise MT5ServiceError(f"No unique open position {ticket} on {symbol}")
        position = rows[0]
        closing_buy = self.position_side(position["type"]) == "buy"
        tick = self._quote(self, settings)
        if Decimal(str(tick["ask"])) - Decimal(str(tick["bid"])) > settings.MAX_SPREAD:
            raise MT5ServiceError("Spread exceeds MAX_SPREAD")
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "type": (
                self.mt5.ORDER_TYPE_SELL if closing_buy else self.mt5.ORDER_TYPE_BUY
            ),
            "volume": self._volume(self.symbol_info(symbol), position["volume"]),
            "price": tick["bid" if closing_buy else "ask"],
            "magic": settings.MT5_MAGIC,
            "deviation": self.deviation,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.get_filling_mode(symbol),
            "comment": "FoxBot close",
        }
        return self._checked_request(request, submit)

    def deals_between(self, start: int, end: int) -> list[dict[str, Any]]:
        return self._records(
            f"mt5.history_deals_get({int(start)}, {int(end)})", "history_deals_get"
        )

    def get_filling_mode(self, symbol: str) -> int:
        info = self.symbol_info(symbol)
        flags = info["filling_mode"]
        if flags & 1:  # SYMBOL_FILLING_FOK
            return self.mt5.ORDER_FILLING_FOK
        if flags & 2:  # SYMBOL_FILLING_IOC
            return self.mt5.ORDER_FILLING_IOC
        if info["trade_exemode"] != self.mt5.SYMBOL_TRADE_EXECUTION_MARKET:
            return self.mt5.ORDER_FILLING_RETURN
        raise MT5ServiceError(f"No supported market filling mode for {symbol}")

    @staticmethod
    def _decimal(
        value: float | Decimal, name: str, *, allow_zero: bool = False
    ) -> Decimal:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"{name} must be a valid number") from exc
        if not number.is_finite() or number < 0 or (number == 0 and not allow_zero):
            raise ValueError(
                f"{name} must be {'nonnegative' if allow_zero else 'positive'}"
            )
        return number

    def _volume(self, info: dict[str, Any], volume: float | Decimal) -> float:
        lots = self._decimal(volume, "volume")
        minimum = self._decimal(info["volume_min"], "volume_min")
        maximum = self._decimal(info["volume_max"], "volume_max")
        step = self._decimal(info["volume_step"], "volume_step")
        if not minimum <= lots <= maximum:
            raise ValueError(f"volume must be between {minimum} and {maximum} lots")
        if lots % step != 0:
            raise ValueError(f"volume must be a multiple of {step} lots")
        return float(lots)

    def market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        volume: float | Decimal,
        *,
        sl: float | Decimal | None = None,
        tp: float | Decimal | None = None,
        entry: float | Decimal | None = None,
        submit: bool = False,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        """Preview or submit an order. Use the supplied lot volume."""
        settings = settings or get_settings()
        if symbol != settings.MT5_SYMBOL:
            raise ValueError(f"Expected configured symbol {settings.MT5_SYMBOL}")
        if sl is None or tp is None:
            raise ValueError("Provide both a stop loss and a take profit")
        order = MarketOrder(
            side=side,
            entry=self._decimal(entry, "entry") if entry is not None else None,
            stop=self._decimal(sl, "sl"),
            target=self._decimal(tp, "tp"),
            volume=self._decimal(volume, "volume"),
        )
        return self.execute_market_order(self, settings, order, submit=submit)

    def buy(
        self,
        symbol: str,
        volume: float | Decimal,
        *,
        sl: float | Decimal | None = None,
        tp: float | Decimal | None = None,
        entry: float | Decimal | None = None,
        submit: bool = False,
    ) -> dict[str, Any]:
        return self.market_order(
            symbol,
            "buy",
            volume,
            sl=sl,
            tp=tp,
            entry=entry,
            submit=submit,
        )

    def sell(
        self,
        symbol: str,
        volume: float | Decimal,
        *,
        sl: float | Decimal | None = None,
        tp: float | Decimal | None = None,
        entry: float | Decimal | None = None,
        submit: bool = False,
    ) -> dict[str, Any]:
        return self.market_order(
            symbol,
            "sell",
            volume,
            sl=sl,
            tp=tp,
            entry=entry,
            submit=submit,
        )

    @staticmethod
    def _validate_settings(settings: Settings) -> None:
        if not re.fullmatch(r"XAUUSD[A-Za-z0-9._-]*", settings.MT5_SYMBOL):
            raise ValueError("MT5_SYMBOL must be XAUUSD or XAUUSD with a broker suffix")
        if settings.MT5_MAGIC <= 0:
            raise ValueError("MT5_MAGIC must be positive")

    @staticmethod
    def _quote(mt5: MT5Service, settings: Settings) -> dict[str, Any]:
        tick = mt5.tick(settings.MT5_SYMBOL)
        stamp = tick.get("time_msc")
        if type(stamp) is not int or stamp <= 0:
            raise MT5ServiceError(
                f"MT5 returned no valid tick timestamp for {settings.MT5_SYMBOL}"
            )
        quote_utc = stamp / 1000 - settings.mt5_quote_utc_offset_seconds
        age = time() - quote_utc
        if age < 0:
            raise MT5ServiceError(
                f"MT5 quote for {settings.MT5_SYMBOL} is {-age:.2f}s ahead of the local clock. "
                "Check clock synchronization and MT5_QUOTE_UTC_OFFSET_MINUTES"
            )
        if age > settings.MAX_QUOTE_AGE_SECONDS:
            raise MT5ServiceError(
                f"MT5 quote for {settings.MT5_SYMBOL} is stale ({age:.2f}s old, "
                f"limit {settings.MAX_QUOTE_AGE_SECONDS}s)"
            )
        return tick

    @staticmethod
    def _order_result(
        mt5: MT5Service,
        result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = mt5.mt5
        result = result or {}
        retcode = result.get("retcode")
        status = "pending"
        if (
            retcode in (api.TRADE_RETCODE_DONE, api.TRADE_RETCODE_DONE_PARTIAL)
            and type(result.get("deal")) is int
            and result["deal"] > 0
        ):
            status = "filled" if retcode == api.TRADE_RETCODE_DONE else "partial"
        elif result.get("guard_blocked") is True or retcode in (
            api.TRADE_RETCODE_REJECT,
            api.TRADE_RETCODE_REQUOTE,
            api.TRADE_RETCODE_INVALID,
            api.TRADE_RETCODE_INVALID_VOLUME,
            api.TRADE_RETCODE_INVALID_STOPS,
            api.TRADE_RETCODE_NO_MONEY,
            api.TRADE_RETCODE_MARKET_CLOSED,
            api.TRADE_RETCODE_PRICE_CHANGED,
        ):
            status = "rejected"
        if status == "pending":
            raise MT5ServiceError(
                f"Order has an uncertain result ({retcode}). Do not resend"
            )
        if status == "rejected":
            reason = (
                "account or quote changed"
                if result.get("guard_blocked")
                else f"retcode {retcode}"
            )
            raise MT5ServiceError(f"Order was rejected ({reason})")
        return {"status": status, **result}

    @staticmethod
    def execute_market_order(
        mt5: MT5Service, settings: Settings, order: MarketOrder, *, submit: bool = False
    ) -> dict[str, Any]:
        """Check a manual order and optionally submit it once."""
        MT5Service._validate_settings(settings)
        if submit and not settings.ENABLE_TRADING:
            raise MT5ServiceError("Order submission requires ENABLE_TRADING=true")

        tick = MT5Service._quote(mt5, settings)
        bid, ask = Decimal(str(tick["bid"])), Decimal(str(tick["ask"]))
        price = ask if order.side == "buy" else bid
        if ask - bid > settings.MAX_SPREAD:
            raise MT5ServiceError("Spread exceeds MAX_SPREAD")
        if (
            order.entry is not None
            and abs(price - order.entry) > settings.MAX_ENTRY_DEVIATION
        ):
            raise MT5ServiceError("Price exceeds MAX_ENTRY_DEVIATION")
        info = mt5.symbol_info(settings.MT5_SYMBOL)
        request = {
            "action": mt5.mt5.TRADE_ACTION_DEAL,
            "symbol": settings.MT5_SYMBOL,
            "volume": mt5._volume(info, order.volume),
            "type": (
                mt5.mt5.ORDER_TYPE_BUY
                if order.side == "buy"
                else mt5.mt5.ORDER_TYPE_SELL
            ),
            "price": float(price),
            "sl": float(order.stop),
            "tp": float(order.target),
            "magic": settings.MT5_MAGIC,
            "deviation": mt5.deviation,
            "type_time": mt5.mt5.ORDER_TIME_GTC,
            "type_filling": mt5.get_filling_mode(settings.MT5_SYMBOL),
            "comment": "FoxBot",
        }

        return mt5._checked_request(request, submit)

    def _checked_request(self, request: dict[str, Any], submit: bool) -> dict[str, Any]:
        def call(method: str) -> dict[str, Any]:
            result = self._eval(
                "(lambda row: {k: v for k, v in row._asdict().items() if k != 'request'} "
                f"if row is not None else None)(mt5.{method}({request!r}))"
            )
            if result is None:
                raise MT5ServiceError(f"{method} failed: {self.last_error()}")
            return result

        check = call("order_check")
        if check.get("retcode") != 0:
            raise MT5ServiceError(f"Broker order check failed: {check.get('comment')}")
        if not submit:
            return {"status": "dry_run", **request}

        try:
            result = call("order_send")
        except MT5ServiceError as exc:
            raise MT5ServiceError(
                "Order has an uncertain outcome. Do not resend"
            ) from exc
        return self._order_result(self, result)


execute_market_order = MT5Service.execute_market_order
