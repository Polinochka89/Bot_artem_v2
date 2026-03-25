from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ExchangeRateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    result: str
    conversion_rates: dict[str, float]
