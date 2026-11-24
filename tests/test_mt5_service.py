from collections import namedtuple
from decimal import Decimal
from time import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from mt5linux import MetaTrader5
from pydantic import ValidationError

from bot.core.cli import main
from bot.core.settings import Settings
from bot.schemas.mt5.data.market_order import MarketOrder
from bot.services import mt5
from bot.services.mt5 import (
    MT5Service,
    MT5ServiceError,
)

SYMBOL = "XAUUSD.m"


def record(**fields):
    return namedtuple("MT5Record", fields)(**fields)


@pytest.fixture
def bridge(monkeypatch):
    remote = SimpleNamespace(
        account_info=Mock(
            return_value=record(
                trade_mode=MetaTrader5.ACCOUNT_TRADE_MODE_DEMO,
                login=1234,
                trade_allowed=True,
                trade_expert=True,
            ),
        ),
        last_error=Mock(return_value=(-1, "terminal error")),
        symbol_info=Mock(
            return_value=record(
                visible=True,
                filling_mode=1,
                trade_exemode=MetaTrader5.SYMBOL_TRADE_EXECUTION_MARKET,
                volume_min=0.01,
                volume_max=10,
                volume_step=0.01,
            ),
        ),
        symbol_select=Mock(return_value=True),
        symbol_info_tick=Mock(return_value=record(bid=2500, ask=2500.25)),
        positions_get=Mock(
            return_value=(
                record(
                    ticket=42,
                    symbol=SYMBOL,
                    volume=0.05,
                    type=MetaTrader5.POSITION_TYPE_BUY,
                    sl=2490,
                    tp=2510,
                ),
            ),
        ),
        orders_get=Mock(return_value=(record(ticket=17, symbol=SYMBOL),)),
        history_deals_get=Mock(return_value=(record(ticket=23, position_id=42),)),
        order_check=Mock(return_value=record(retcode=0, request=object())),
        order_send=Mock(side_effect=AssertionError("Unexpected order submission")),
    )
    client = Mock(spec=MetaTrader5)
    for name in dir(MetaTrader5):
        if name.isupper():
            setattr(client, name, getattr(MetaTrader5, name))
    client.initialize.return_value = True
    client.login.return_value = True
    client.eval.side_effect = lambda expression: eval(
        expression,
        {"mt5": remote, "__builtins__": {"dict": dict}},
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(mt5, "MetaTrader5", factory)
    bridge = SimpleNamespace(
        remote=remote,
        client=client,
        factory=factory,
        allow_send=False,
    )
    yield bridge
    if not bridge.allow_send:
        remote.order_send.assert_not_called()


@pytest.fixture
def service(bridge):
    with MT5Service() as connected:
        yield connected


def test_connect_and_disconnect(bridge):
    service = MT5Service(
        "mt5.local",
        18813,
        login=1234,
        password="test-password",
        server="Demo",
    )
    assert service.connect() is service
    assert service.mt5 is bridge.client
    bridge.factory.assert_called_once_with(host="mt5.local", port=18813)
    bridge.client.initialize.assert_called_once_with()
    bridge.client.login.assert_called_once_with(
        1234,
        password="test-password",
        server="Demo",
    )
    with pytest.raises(MT5ServiceError, match="Already connected"):
        service.connect()
    service.disconnect()
    service.disconnect()
    bridge.client.shutdown.assert_called_once_with()
    with pytest.raises(MT5ServiceError, match="not connected"):
        _ = service.mt5


def test_context_manager_cleans_up_on_error(bridge):
    with pytest.raises(RuntimeError, match="operation failed"), MT5Service() as service:
        assert service.mt5 is bridge.client
        raise RuntimeError("operation failed")
    bridge.client.login.assert_not_called()
    bridge.client.shutdown.assert_called_once_with()


@pytest.mark.parametrize(
    "credentials",
    [{"login": 1234}, {"password": ""}, {"server": "Demo"}],
)
def test_connect_rejects_partial_credentials(bridge, credentials):
    with pytest.raises(ValueError, match="together"):
        MT5Service(**credentials).connect()
    bridge.factory.assert_not_called()


@pytest.mark.parametrize("stage", ["initialize", "login"])
def test_connect_handles_terminal_failure(bridge, stage):
    getattr(bridge.client, stage).return_value = False
    service = MT5Service(login=1234, password="test-password", server="Demo")
    with pytest.raises(MT5ServiceError, match=r"MT5 .* failed"):
        service.connect()
    bridge.client.shutdown.assert_called_once_with()


def test_connect_sanitizes_bridge_failure(bridge):
    bridge.factory.side_effect = OSError("bridge details")
    with pytest.raises(MT5ServiceError, match=r"^MT5 connection failed$"):
        MT5Service().connect()
    bridge.client.shutdown.assert_not_called()


def test_disconnect_clears_connection_even_if_shutdown_fails(bridge):
    service = MT5Service().connect()
    bridge.client.shutdown.side_effect = OSError("bridge unavailable")
    with pytest.raises(MT5ServiceError, match="shutdown failed"):
        service.disconnect()
    with pytest.raises(MT5ServiceError, match="not connected"):
        _ = service.mt5


def test_account_and_last_error(service, bridge):
    assert service.account() == dict(bridge.remote.account_info.return_value._asdict())
    assert service.last_error() == (-1, "terminal error")


def test_read_wraps_bridge_error(service, bridge):
    bridge.client.eval.side_effect = EOFError
    with pytest.raises(MT5ServiceError, match="bridge call failed"):
        service.account()


def test_symbol_info_selects_hidden_symbol(service, bridge):
    info = bridge.remote.symbol_info.return_value
    bridge.remote.symbol_info.side_effect = [info._replace(visible=False), info]
    assert service.symbol_info(SYMBOL)["visible"] is True
    bridge.remote.symbol_select.assert_called_once_with(SYMBOL, True)


@pytest.mark.parametrize("selects", [False, True])
def test_symbol_info_rejects_unavailable_symbol(service, bridge, selects):
    bridge.remote.symbol_info.return_value = record(visible=False)
    bridge.remote.symbol_select.return_value = selects
    with pytest.raises(MT5ServiceError, match=r"Cannot enable|still not visible"):
        service.symbol_info(SYMBOL)


def test_tick(service, bridge):
    assert service.tick(SYMBOL) == {"bid": 2500, "ask": 2500.25}
    bridge.remote.symbol_info_tick.assert_called_once_with(SYMBOL)


@pytest.mark.parametrize(("bid", "ask"), [(0, 1), (2, 1), (1, float("nan"))])
def test_tick_rejects_bad_prices(service, bridge, bid, ask):
    bridge.remote.symbol_info_tick.return_value = record(bid=bid, ask=ask)
    with pytest.raises(MT5ServiceError, match="Invalid tick prices"):
        service.tick(SYMBOL)


@pytest.fixture
def execution(bridge, tmp_path):
    api = MetaTrader5
    remote = bridge.remote
    remote.account_info.return_value = record(
        trade_mode=api.ACCOUNT_TRADE_MODE_DEMO,
        login=1234,
        server="Broker",
        trade_allowed=True,
        trade_expert=True,
        equity=10000.0,
        balance=10000.0,
        margin_free=10000.0,
        credit=0.0,
    )
    remote.symbol_info.return_value = record(
        visible=True,
        filling_mode=1,
        trade_exemode=api.SYMBOL_TRADE_EXECUTION_MARKET,
        trade_mode=api.SYMBOL_TRADE_MODE_FULL,
        point=0.01,
        trade_tick_size=0.01,
        trade_stops_level=10,
        trade_freeze_level=0,
        volume_min=0.01,
        volume_max=10,
        volume_step=0.01,
    )
    remote.symbol_info_tick.return_value = record(
        bid=2500,
        ask=2500.25,
        time_msc=int(time() * 1000),
    )
    remote.terminal_info = Mock(
        return_value=record(
            connected=True, trade_allowed=True, tradeapi_disabled=False
        ),
    )
    remote.positions_get.return_value = ()
    remote.orders_get.return_value = ()
    remote.history_deals_get.return_value = ()
    remote.order_calc_profit = Mock(
        side_effect=lambda _side, _symbol, lots, entry, stop: (
            -round(abs(entry - stop) * lots * 100, 8)
        ),
    )
    remote.order_calc_margin = Mock(return_value=100)
    remote.order_check.return_value = record(
        retcode=0,
        margin_free=9900,
        request=object(),
    )
    remote.order_send.side_effect = None
    remote.order_send.return_value = record(
        retcode=api.TRADE_RETCODE_DONE,
        deal=123,
        order=456,
    )
    settings = Settings(
        _env_file=None,
        ENABLE_TRADING=True,
        ENABLE_REAL_TRADING=False,
        MT5_SYMBOL=SYMBOL,
        MT5_LOGIN=1234,
        MT5_SERVER="Broker",
        MT5_PASSWORD="fixture-password",
        MT5_SLIPPAGE_ALLOWANCE="0.25",
        MT5_ROUND_TRIP_COST_PER_LOT="5",
    )
    order = MarketOrder(
        side="buy",
        entry=Decimal(2500),
        stop=Decimal(2498),
        target=Decimal(2504),
        volume=Decimal(2),
    )
    return bridge, settings, order


@pytest.mark.parametrize(("side", "price"), [("buy", 2500.25), ("sell", 2500)])
def test_fixed_volume_order(execution, monkeypatch, side, price):
    bridge, settings, _ = execution
    monkeypatch.setattr("bot.core.settings.get_settings", lambda: settings)
    bridge.remote.account_info.return_value = record(
        login=45,
        server="Other",
        trade_mode=2,
    )
    args = [
        "mt5",
        "order",
        side,
        "--volume",
        "2",
        "--sl",
        "2498" if side == "buy" else "2504",
        "--tp",
        "2504" if side == "buy" else "2498",
    ]
    runner = CliRunner()
    preview = runner.invoke(main, args)
    assert preview.exit_code == 0, preview.output
    assert str(price) in preview.output
    bridge.remote.order_send.assert_not_called()
    bridge.allow_send = True
    submitted = runner.invoke(main, [*args, "--submit"])
    assert submitted.exit_code == 0, submitted.output
    request = bridge.remote.order_send.call_args.args[0]
    assert request["volume"] == 2
    assert request["price"] == price
    bridge.remote.order_send.assert_called_once()
    bridge.remote.order_calc_profit.assert_not_called()
    bridge.remote.order_calc_margin.assert_not_called()


def test_broker_check_failure_blocks_send(execution):
    bridge, settings, order = execution
    bridge.remote.order_check.return_value = record(retcode=1, comment="invalid stops")
    with MT5Service() as service, pytest.raises(MT5ServiceError, match="invalid stops"):
        MT5Service.execute_market_order(service, settings, order, submit=True)


def test_uncertain_send_reports_failure_without_retry(execution):
    bridge, settings, order = execution
    bridge.allow_send = True
    bridge.remote.order_send.side_effect = OSError("bridge disconnected")
    with MT5Service() as service, pytest.raises(MT5ServiceError, match="uncertain"):
        MT5Service.execute_market_order(service, settings, order, submit=True)
    bridge.remote.order_send.assert_called_once()


@pytest.mark.parametrize(
    "changes",
    [{"volume": Decimal(0)}, {"stop": Decimal(2501)}, {"side": "hold"}],
)
def test_market_order_schema_rejects_invalid_fields(execution, changes):
    _, _, order = execution
    with pytest.raises(ValidationError):
        MarketOrder.model_validate(order.model_dump() | changes)


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_nested_market_order(execution, monkeypatch, side):
    bridge, settings, _ = execution
    monkeypatch.setattr("bot.core.settings.get_settings", lambda: settings)
    stop, target = ("2498", "2504") if side == "buy" else ("2504", "2498")
    result = CliRunner().invoke(
        main,
        ["mt5", "order", side, "--volume", "0.02", "--sl", stop, "--tp", target],
    )
    assert result.exit_code == 0, result.output
    assert f"Preview {side} 0.02 lots" in result.output

    bridge.allow_send = True
    submitted = CliRunner().invoke(
        main,
        [
            "mt5",
            "order",
            side,
            "--volume",
            "0.02",
            "--sl",
            stop,
            "--tp",
            target,
            "--submit",
        ],
    )
    assert submitted.exit_code == 0, submitted.output
    bridge.remote.order_send.assert_called_once()


@pytest.mark.parametrize("is_buy", [True, False])
def test_list_and_close_position(execution, monkeypatch, is_buy):
    bridge, settings, _ = execution
    monkeypatch.setattr("bot.core.settings.get_settings", lambda: settings)
    api = bridge.client
    bridge.remote.positions_get.return_value = (
        record(
            ticket=42,
            symbol=SYMBOL,
            volume=0.02,
            type=api.POSITION_TYPE_BUY if is_buy else api.POSITION_TYPE_SELL,
        ),
    )
    runner = CliRunner()
    args = ["mt5", "order"]
    all_positions = runner.invoke(main, [*args, "list"])
    assert all_positions.exit_code == 0
    assert SYMBOL in all_positions.output
    listed = runner.invoke(main, [*args, "list", "--ticket", "42"])
    assert listed.exit_code == 0
    assert SYMBOL in listed.output
    for cell in ("Open positions", "Ticket", "Symbol", "Side", "Lots", "42", "0.02"):
        assert cell in listed.output
    empty = runner.invoke(main, [*args, "list", "--ticket", "43"])
    assert empty.exit_code == 0
    assert "No matching open positions." in empty.output
    missing = runner.invoke(main, [*args, "close", "43", "--submit"])
    assert missing.exit_code == 1
    assert "43" in missing.output
    preview = runner.invoke(main, [*args, "close", "42"])
    assert preview.exit_code == 0
    assert "Preview close 42" in preview.output
    bridge.remote.order_send.assert_not_called()
    bridge.allow_send = True
    submitted = runner.invoke(main, [*args, "close", "42", "--submit"])
    assert submitted.exit_code == 0, submitted.output
    request = bridge.remote.order_send.call_args.args[0]
    assert request == bridge.remote.order_check.call_args.args[0]
    assert request["position"] == 42
    assert request["volume"] == 0.02
    assert request["type"] == (api.ORDER_TYPE_SELL if is_buy else api.ORDER_TYPE_BUY)
    assert request["price"] == (2500 if is_buy else 2500.25)
