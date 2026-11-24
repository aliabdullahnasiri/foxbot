from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveDecimal = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


class MarketOrder(BaseModel):
    """Validated inputs for a manual market position."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    side: Literal["buy", "sell"]
    entry: PositiveDecimal | None
    stop: PositiveDecimal
    target: PositiveDecimal
    volume: PositiveDecimal

    @model_validator(mode="after")
    def check_price_levels(self) -> Self:
        if self.entry is None:
            return self
        lower, upper = (
            (self.stop, self.target) if self.side == "buy" else (self.target, self.stop)
        )
        if not lower < self.entry < upper:
            raise ValueError(
                "SL and TP must be on the correct sides of the intended entry",
            )
        return self
