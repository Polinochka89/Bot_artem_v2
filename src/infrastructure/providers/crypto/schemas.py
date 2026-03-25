from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CoinGeckoPriceData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    usd: float
    usd_24h_change: float | None = None


class CoinCapAssetData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    symbol: str
    price_usd: str = Field(alias="priceUsd")
    change_percent_24hr: str | None = Field(default=None, alias="changePercent24Hr")


class CoinCapResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[CoinCapAssetData]
