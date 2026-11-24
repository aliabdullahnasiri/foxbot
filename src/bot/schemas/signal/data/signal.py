from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Price = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


class SignalData(BaseModel):
    """A structurally valid extraction awaiting source-text verification."""

    model_config = ConfigDict(extra="forbid", strict=True)

    symbol: Literal["XAUUSD"]
    side: Literal["BUY", "SELL"]
    entry_price: Price
    stop_loss: Price
    take_profits: list[Price] = Field(min_length=1)

    @model_validator(mode="after")
    def check_price_levels(self) -> Self:
        if self.side == "BUY":
            if not self.stop_loss < self.entry_price < min(self.take_profits):
                raise ValueError(
                    "BUY requires SL below entry and every TP above entry.",
                )
        elif not max(self.take_profits) < self.entry_price < self.stop_loss:
            raise ValueError("SELL requires SL above entry and every TP below entry.")
        return self
