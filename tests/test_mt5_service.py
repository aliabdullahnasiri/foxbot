from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from mt5linux import MetaTrader5

from bot.services import mt5
from bot.services.mt5 import MT5Service, MT5ServiceError

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
            )
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
            )
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
            )
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
        expression, {"mt5": remote, "__builtins__": {"dict": dict}}
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(mt5, "MetaTrader5", factory)
    yield SimpleNamespace(remote=remote, client=client, factory=factory)
    remote.order_send.assert_not_called()


@pytest.fixture
def service(bridge):
    with MT5Service() as connected:
        yield connected


def test_connect_and_disconnect(bridge):
    service = MT5Service(
        "mt5.local", 18813, login=1234, password="test-password", server="Demo"
    )
    assert service.connect() is service
    assert service.mt5 is bridge.client
    bridge.factory.assert_called_once_with(host="mt5.local", port=18813)
    bridge.client.initialize.assert_called_once_with()
    bridge.client.login.assert_called_once_with(
        1234, password="test-password", server="Demo"
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
    "credentials", [{"login": 1234}, {"password": ""}, {"server": "Demo"}]
)
def test_connect_rejects_partial_credentials(bridge, credentials):
    with pytest.raises(ValueError, match="together"):
        MT5Service(**credentials).connect()
    bridge.factory.assert_not_called()


def test_constructor_rejects_disabling_demo_mode():
    with pytest.raises(ValueError, match="requires a demo account"):
        MT5Service(demo_only=False)


@pytest.mark.parametrize(
    ("account", "error"),
    [
        (record(trade_mode=MetaTrader5.ACCOUNT_TRADE_MODE_REAL), "Only demo"),
        (record(login=1234), "Only demo"),
        (record(trade_mode=False), "Only demo"),
        (
            record(trade_mode=MetaTrader5.ACCOUNT_TRADE_MODE_DEMO, login=999),
            "wrong account",
        ),
        (None, "account_info failed"),
    ],
)
def test_connect_rejects_unverified_account(bridge, account, error):
    bridge.remote.account_info.return_value = account
    service = MT5Service(login=1234, password="test-password", server="Demo")
    with pytest.raises(MT5ServiceError, match=error):
        service.connect()
    bridge.client.shutdown.assert_called_once_with()
    with pytest.raises(MT5ServiceError, match="not connected"):
        _ = service.mt5


@pytest.mark.parametrize("stage", ["initialize", "login"])
def test_connect_handles_terminal_failure(bridge, stage):
    getattr(bridge.client, stage).return_value = False
    service = MT5Service(login=1234, password="test-password", server="Demo")
    with pytest.raises(MT5ServiceError, match="MT5 .* failed"):
        service.connect()
    bridge.client.shutdown.assert_called_once_with()


def test_connect_sanitizes_bridge_failure(bridge):
    bridge.factory.side_effect = OSError("bridge details")
    with pytest.raises(MT5ServiceError, match="^MT5 connection failed$"):
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
    with pytest.raises(MT5ServiceError, match="Cannot enable|still not visible"):
        service.symbol_info(SYMBOL)


def test_tick(service, bridge):
    assert service.tick(SYMBOL) == {"bid": 2500, "ask": 2500.25}
    bridge.remote.symbol_info_tick.assert_called_once_with(SYMBOL)


@pytest.mark.parametrize(("bid", "ask"), [(0, 1), (2, 1), (1, float("nan"))])
def test_tick_rejects_bad_prices(service, bridge, bid, ask):
    bridge.remote.symbol_info_tick.return_value = record(bid=bid, ask=ask)
    with pytest.raises(MT5ServiceError, match="Invalid tick prices"):
        service.tick(SYMBOL)


@pytest.mark.parametrize(
    ("many", "one", "api", "ticket"),
    [
        ("positions", "position", "positions_get", 42),
        ("pending_orders", "pending_order", "orders_get", 17),
    ],
)
def test_position_and_pending_order_queries(service, bridge, many, one, api, ticket):
    query = getattr(bridge.remote, api)
    list_entries, get_entry = getattr(service, many), getattr(service, one)
    assert list_entries()[0]["ticket"] == ticket
    query.assert_called_once_with()
    assert list_entries(SYMBOL)[0]["ticket"] == ticket
    query.assert_called_with(symbol=SYMBOL)
    assert get_entry(ticket)["ticket"] == ticket
    query.assert_called_with(ticket=ticket)
    query.return_value = ()
    assert list_entries() == []
    assert get_entry(ticket) is None
    query.return_value = None
    with pytest.raises(MT5ServiceError, match=f"{api} failed"):
        list_entries()


def test_history_deals(service, bridge):
    assert service.history_deals(42) == [{"ticket": 23, "position_id": 42}]
    bridge.remote.history_deals_get.assert_called_once_with(position=42)


@pytest.mark.parametrize(
    ("flags", "execution", "mode"),
    [
        (3, MetaTrader5.SYMBOL_TRADE_EXECUTION_MARKET, MetaTrader5.ORDER_FILLING_FOK),
        (2, MetaTrader5.SYMBOL_TRADE_EXECUTION_MARKET, MetaTrader5.ORDER_FILLING_IOC),
        (
            0,
            MetaTrader5.SYMBOL_TRADE_EXECUTION_INSTANT,
            MetaTrader5.ORDER_FILLING_RETURN,
        ),
        (0, MetaTrader5.SYMBOL_TRADE_EXECUTION_MARKET, None),
    ],
)
def test_get_filling_mode(service, bridge, flags, execution, mode):
    bridge.remote.symbol_info.return_value = record(
        visible=True, filling_mode=flags, trade_exemode=execution
    )
    if mode is None:
        with pytest.raises(MT5ServiceError, match="No supported market filling mode"):
            service.get_filling_mode(SYMBOL)
    else:
        assert service.get_filling_mode(SYMBOL) == mode


@pytest.mark.parametrize("retcode", [0, 10019])
def test_order_check_returns_broker_result_without_nested_request(
    service, bridge, retcode
):
    request = {"symbol": SYMBOL, "comment": "'quoted'\ntext"}
    bridge.remote.order_check.return_value = record(retcode=retcode, request=object())
    assert service.order_check(request) == {"retcode": retcode}
    bridge.remote.order_check.assert_called_once_with(request)


def test_order_check_distinguishes_api_failure(service, bridge):
    bridge.remote.order_check.return_value = None
    with pytest.raises(MT5ServiceError, match="order_check failed"):
        service.order_check({"symbol": SYMBOL})


@pytest.mark.parametrize(
    ("account", "error"),
    [
        ({"trade_mode": MetaTrader5.ACCOUNT_TRADE_MODE_REAL}, "Only demo"),
        ({"trade_allowed": False}, "Trading or automated trading is disabled"),
        ({"trade_expert": False}, "Trading or automated trading is disabled"),
    ],
)
def test_order_check_revalidates_account(service, bridge, account, error):
    bridge.remote.account_info.return_value = (
        bridge.remote.account_info.return_value._replace(**account)
    )
    with pytest.raises(MT5ServiceError, match=error):
        service.order_check({"symbol": SYMBOL})
    bridge.remote.order_check.assert_not_called()


@pytest.mark.parametrize("value", [object(), float("inf"), float("nan")])
def test_order_check_rejects_nonliteral_values(service, bridge, value):
    with pytest.raises(ValueError, match="Order check requires"):
        service.order_check({"volume": value})
    bridge.remote.order_check.assert_not_called()


@pytest.mark.parametrize(
    ("method", "args", "order_type", "price", "sl", "tp"),
    [
        ("market_order", ("buy",), MetaTrader5.ORDER_TYPE_BUY, 2500.25, 2490, 2510),
        ("buy", (), MetaTrader5.ORDER_TYPE_BUY, 2500.25, 2490, 2510),
        ("sell", (), MetaTrader5.ORDER_TYPE_SELL, 2500, 2510, 2490),
    ],
)
def test_market_request(service, monkeypatch, method, args, order_type, price, sl, tp):
    send = Mock(return_value={"retcode": 10009})
    monkeypatch.setattr(service, "_send", send)
    assert (
        getattr(service, method)(SYMBOL, *args, 0.05, sl=sl, tp=tp, comment="test")
        == send.return_value
    )
    send.assert_called_once_with(
        {
            "action": MetaTrader5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": 0.05,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "test",
            "type_time": MetaTrader5.ORDER_TIME_GTC,
            "type_filling": MetaTrader5.ORDER_FILLING_FOK,
            "sl": sl,
            "tp": tp,
        }
    )


@pytest.mark.parametrize(
    ("side", "volume", "sl", "error"),
    [
        ("hold", 0.05, 2490, "side must"),
        ("buy", float("nan"), 2490, "volume must be positive"),
        ("buy", 0.001, 2490, "between"),
        ("buy", 10.01, 2490, "between"),
        ("buy", 0.015, 2490, "multiple"),
        ("buy", 0.05, 0, "sl must be positive"),
    ],
)
def test_market_order_rejects_invalid_input(service, side, volume, sl, error):
    with pytest.raises(ValueError, match=error):
        service.market_order(SYMBOL, side, volume, sl=sl)


@pytest.mark.parametrize(
    ("direction", "volume", "order_type", "price", "lots"),
    [
        (MetaTrader5.POSITION_TYPE_BUY, None, MetaTrader5.ORDER_TYPE_SELL, 2500, 0.05),
        (
            MetaTrader5.POSITION_TYPE_SELL,
            0.02,
            MetaTrader5.ORDER_TYPE_BUY,
            2500.25,
            0.02,
        ),
    ],
)
def test_close_position(
    service, bridge, monkeypatch, direction, volume, order_type, price, lots
):
    position = bridge.remote.positions_get.return_value[0]
    bridge.remote.positions_get.return_value = (position._replace(type=direction),)
    send = Mock()
    monkeypatch.setattr(service, "_send", send)
    assert service.close_position(42, volume=volume) is send.return_value
    request = send.call_args.args[0]
    assert request["position"] == 42
    assert request["type"] == order_type
    assert request["price"] == price
    assert request["volume"] == lots


def test_close_position_rejects_excess_volume(service):
    with pytest.raises(ValueError, match="<= position volume"):
        service.close_position(42, volume=0.06)


def test_update_stops_preserves_omitted_stop(service, monkeypatch):
    send = Mock()
    monkeypatch.setattr(service, "_send", send)
    assert service.update_stops(42, tp=0) is send.return_value
    send.assert_called_once_with(
        {
            "action": MetaTrader5.TRADE_ACTION_SLTP,
            "position": 42,
            "symbol": SYMBOL,
            "sl": 2490,
            "tp": 0,
        }
    )


def test_update_stops_requires_a_change_and_prohibits_removing_sl(service):
    with pytest.raises(ValueError, match="Provide sl or tp"):
        service.update_stops(42)
    with pytest.raises(ValueError, match="sl must be positive"):
        service.update_stops(42, sl=0)


@pytest.mark.parametrize(
    ("method", "kwargs"), [("close_position", {}), ("update_stops", {"sl": 2490})]
)
def test_position_changes_require_an_open_ticket(service, bridge, method, kwargs):
    bridge.remote.positions_get.return_value = ()
    with pytest.raises(MT5ServiceError, match="Position 42 is not open"):
        getattr(service, method)(42, **kwargs)


def test_place_pending_is_outside_v1(service):
    with pytest.raises(MT5ServiceError, match="outside FoxBot v1"):
        service.place_pending(SYMBOL, "buy", "limit", 0.05, 2498, sl=2490, tp=2510)


def test_cancel_pending_order(service, bridge, monkeypatch):
    send = Mock()
    monkeypatch.setattr(service, "_send", send)
    assert service.cancel_pending_order(17) is send.return_value
    send.assert_called_once_with(
        {"action": MetaTrader5.TRADE_ACTION_REMOVE, "order": 17}
    )
    bridge.remote.orders_get.return_value = ()
    with pytest.raises(MT5ServiceError, match="Pending order 17 not found"):
        service.cancel_pending_order(17)


@pytest.mark.parametrize("enabled", ["false", "true"])
def test_order_submission_is_blocked_until_execution_controls_exist(
    service, monkeypatch, enabled
):
    monkeypatch.setenv("ENABLE_TRADING", enabled)
    with pytest.raises(MT5ServiceError, match="Order submission is unavailable"):
        service.buy(SYMBOL, 0.05, sl=2490, tp=2510)
    with pytest.raises(MT5ServiceError, match="Order submission is unavailable"):
        service.close_position(42)
    with pytest.raises(MT5ServiceError, match="Order submission is unavailable"):
        service.update_stops(42, sl=2491)
    with pytest.raises(MT5ServiceError, match="Order submission is unavailable"):
        service.cancel_pending_order(17)
