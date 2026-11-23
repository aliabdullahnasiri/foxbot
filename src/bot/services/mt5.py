"""Synchronous MetaTrader 5 adapter for the mt5linux bridge."""

from decimal import Decimal, InvalidOperation
from math import isfinite
from types import TracebackType
from typing import Any, Literal, Self

from mt5linux import MetaTrader5


class MT5ServiceError(RuntimeError):
    """MT5 connection, validation, or API failure."""


class MT5Service:
    """Connect to a demo terminal and use plain Python values across RPyC."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18812,
        *,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        demo_only: bool = True,
        magic: int = 123456,
        deviation: int = 20,
    ) -> None:
        if demo_only is not True:
            raise ValueError("FoxBot requires a demo account")
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
        """Initialize the terminal, optionally log in, and verify demo mode."""
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
            self._verify_account()
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

    def _verify_account(self, *, for_trading: bool = False) -> dict[str, Any]:
        account = self.account()
        mode = account.get("trade_mode")
        if type(mode) is not int or mode != self.mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise MT5ServiceError("Only demo accounts are allowed")
        if self.login is not None and account.get("login") != self.login:
            raise MT5ServiceError("MT5 is connected to the wrong account")
        if for_trading and not (
            account.get("trade_allowed") is True and account.get("trade_expert") is True
        ):
            raise MT5ServiceError("Trading or automated trading is disabled")
        return account

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

    def positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        args = f"symbol={str.__repr__(symbol)}" if symbol is not None else ""
        return self._records(f"mt5.positions_get({args})", "positions_get")

    def position(self, ticket: int) -> dict[str, Any] | None:
        matches = self._records(
            f"mt5.positions_get(ticket={int(ticket)})", "positions_get"
        )
        return matches[0] if matches else None

    def pending_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        args = f"symbol={str.__repr__(symbol)}" if symbol is not None else ""
        return self._records(f"mt5.orders_get({args})", "orders_get")

    def pending_order(self, ticket: int) -> dict[str, Any] | None:
        matches = self._records(f"mt5.orders_get(ticket={int(ticket)})", "orders_get")
        return matches[0] if matches else None

    def history_deals(self, position_ticket: int) -> list[dict[str, Any]]:
        return self._records(
            f"mt5.history_deals_get(position={int(position_ticket)})",
            "history_deals_get",
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

    def _send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Fail closed until FoxBot can enforce execution and recovery controls."""
        raise MT5ServiceError("Order submission is unavailable in the MT5 adapter")

    def order_check(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return the broker's preflight result without changing any orders."""
        self._verify_account(for_trading=True)
        fields = dict(request)
        # Only built-in literals may be embedded in the remote call.
        for key, value in fields.items():
            if type(key) is not str or type(value) not in (str, int, float, bool):
                raise ValueError("Order check requires string keys and scalar values")
            if type(value) is float and not isfinite(value):
                raise ValueError("Order check requires finite numbers")
        result = self._eval(
            "(lambda row: {key: value for key, value in row._asdict().items() "
            "if key != 'request'} if row is not None else None)"
            f"(mt5.order_check({fields!r}))"
        )
        if result is None:
            raise MT5ServiceError(f"order_check failed: {self.last_error()}")
        return result

    def market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        volume: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "FoxBot Market",
    ) -> dict[str, Any]:
        return self._send(
            self._market_order_request(
                symbol, side, volume, sl=sl, tp=tp, comment=comment
            )
        )

    def check_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        volume: float,
        *,
        sl: float,
        tp: float,
    ) -> dict[str, Any]:
        """Check a hypothetical market order with the demo broker."""
        if sl is None or tp is None:
            raise ValueError("Provide both SL and TP for a market order check")
        request = self._market_order_request(
            symbol, side, volume, sl=sl, tp=tp, comment="FoxBot Market"
        )
        price = request["price"]
        if side == "buy" and not request["sl"] < price < request["tp"]:
            raise ValueError("BUY requires SL below the current ask and TP above it")
        if side == "sell" and not request["tp"] < price < request["sl"]:
            raise ValueError("SELL requires TP below the current bid and SL above it")
        return self.order_check(request)

    def _market_order_request(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        volume: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "FoxBot Market",
    ) -> dict[str, Any]:
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        info = self.symbol_info(symbol)
        tick = self.tick(symbol)
        is_buy = side == "buy"
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self._volume(info, volume),
            "type": self.mt5.ORDER_TYPE_BUY if is_buy else self.mt5.ORDER_TYPE_SELL,
            "price": tick["ask"] if is_buy else tick["bid"],
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.get_filling_mode(symbol),
        }
        if sl is not None:
            request["sl"] = float(self._decimal(sl, "sl"))
        if tp is not None:
            request["tp"] = float(self._decimal(tp, "tp"))
        return request

    def buy(
        self,
        symbol: str,
        volume: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "FoxBot Market",
    ) -> dict[str, Any]:
        return self.market_order(symbol, "buy", volume, sl=sl, tp=tp, comment=comment)

    def sell(
        self,
        symbol: str,
        volume: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "FoxBot Market",
    ) -> dict[str, Any]:
        return self.market_order(symbol, "sell", volume, sl=sl, tp=tp, comment=comment)

    def close_position(
        self, ticket: int, *, volume: float | None = None
    ) -> dict[str, Any]:
        position = self.position(ticket)
        if position is None:
            raise MT5ServiceError(f"Position {ticket} is not open")
        symbol = position["symbol"]
        info = self.symbol_info(symbol)
        existing = self._decimal(position["volume"], "position volume")
        lots = existing if volume is None else self._decimal(volume, "close volume")
        if lots > existing:
            raise ValueError("close volume must be <= position volume")
        tick = self.tick(symbol)
        position_type = position["type"]
        if position_type not in (
            self.mt5.POSITION_TYPE_BUY,
            self.mt5.POSITION_TYPE_SELL,
        ):
            raise MT5ServiceError(f"Unrecognized direction for position {ticket}")
        is_buy = position_type == self.mt5.POSITION_TYPE_BUY
        return self._send(
            {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "position": int(ticket),
                "volume": self._volume(info, lots),
                "type": self.mt5.ORDER_TYPE_SELL if is_buy else self.mt5.ORDER_TYPE_BUY,
                "price": tick["bid"] if is_buy else tick["ask"],
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": "FoxBot Close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.get_filling_mode(symbol),
            }
        )

    def update_stops(
        self, ticket: int, *, sl: float | None = None, tp: float | None = None
    ) -> dict[str, Any]:
        if sl is None and tp is None:
            raise ValueError("Provide sl or tp")
        position = self.position(ticket)
        if position is None:
            raise MT5ServiceError(f"Position {ticket} is not open")
        return self._send(
            {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "symbol": position["symbol"],
                "position": int(ticket),
                "sl": position["sl"] if sl is None else float(self._decimal(sl, "sl")),
                "tp": (
                    position["tp"]
                    if tp is None
                    else float(self._decimal(tp, "tp", allow_zero=True))
                ),
            }
        )

    def place_pending(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        kind: Literal["limit", "stop"],
        volume: float,
        price: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "FoxBot Pending",
    ) -> dict[str, Any]:
        """Reject pending order placement, which is outside FoxBot v1."""
        raise MT5ServiceError("Pending order placement is outside FoxBot v1")

    def cancel_pending_order(self, ticket: int) -> dict[str, Any]:
        if self.pending_order(ticket) is None:
            raise MT5ServiceError(f"Pending order {ticket} not found")
        return self._send(
            {"action": self.mt5.TRADE_ACTION_REMOVE, "order": int(ticket)}
        )
