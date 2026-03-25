from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TinkoffQuotation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    units: str | int | float
    nano: int | None = None


class TinkoffLastPrice(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    instrument_uid: str | None = Field(default=None, alias="instrumentUid")
    figi: str | None = None
    price: TinkoffQuotation


class TinkoffResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    last_prices: list[TinkoffLastPrice] = Field(alias="lastPrices")
