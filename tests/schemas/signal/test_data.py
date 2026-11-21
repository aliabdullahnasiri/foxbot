from decimal import Decimal

import pytest
from pydantic import ValidationError

from bot.schemas.signal.data.signal import SignalData


@pytest.fixture
def buy():
    return {
        "symbol": "XAUUSD",
        "side": "BUY",
        "entry_price": Decimal("2500.00000000000000001"),
        "stop_loss": Decimal(2500),
        "take_profits": [Decimal(2501), Decimal(2502)],
    }


def test_buy_preserves_prices_and_target_order(buy):
    signal = SignalData.model_validate(buy)
    assert signal.entry_price == buy["entry_price"]
    assert signal.take_profits == buy["take_profits"]


@pytest.mark.parametrize(
    "changes",
    [
        {"symbol": "EURUSD"},
        {"side": "HOLD"},
        {"volume": 1},
        {"entry_price": Decimal(0)},
        {"entry_price": True},
        {"stop_loss": Decimal("NaN")},
        {"stop_loss": Decimal(2600)},
        {"take_profits": []},
        {"take_profits": [Decimal(2510), Decimal(2490)]},
        {"take_profits": [Decimal("Infinity")]},
        {"side": "SELL"},
        {
            "side": "SELL",
            "stop_loss": Decimal(2510),
            "take_profits": [Decimal(2490), Decimal(2501)],
        },
    ],
)
def test_rejects_invalid_extractions(buy, changes):
    with pytest.raises(ValidationError):
        SignalData.model_validate(buy | changes)


def test_stop_loss_is_required(buy):
    del buy["stop_loss"]
    with pytest.raises(ValidationError):
        SignalData.model_validate(buy)
