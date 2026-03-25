import re

with open('scripts/check_providers_live.py', 'r', encoding='utf-8') as f:
    c = f.read()

test_goods = '''        ProviderCheckCase(
            name="yahoo_goods",
            provider=YahooGoodsProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "yahoo_goods", "GC=F"),
                _instrument("OIL", DataCategory.GOODS, "yahoo_goods", "BZ=F"),
            ],
        ),
        ProviderCheckCase(
            name="alphavantage_goods",
            provider=AlphaVantageGoodsProvider(http, CircuitBreaker("alphavantage", 2, 5), retry, alphavantage_key),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "alphavantage_goods", "GLD"),
                _instrument("OIL", DataCategory.GOODS, "alphavantage_goods", "BNO"),
            ],
            missing_credentials_reason=(None if alphavantage_key else "missing ALPHAVANTAGE_API_KEY"),
        ),
        ProviderCheckCase(
            name="twelvedata_goods",
            provider=TwelveDataGoodsProvider(http, CircuitBreaker("twelvedata", 2, 5), retry, twelvedata_key),
            instruments=[
                _instrument("GOLD", DataCategory.GOODS, "twelvedata_goods", "XAU/USD"),
                _instrument("OIL", DataCategory.GOODS, "twelvedata_goods", "BNO"),
            ],
            missing_credentials_reason=(None if twelvedata_key else "missing TWELVE_DATA_API_KEY"),
        ),'''

test_indices = '''        ProviderCheckCase(
            name="yahoo_indices",
            provider=YahooIndicesProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("SPX", DataCategory.INDICES, "yahoo_indices", "^GSPC"),
                _instrument("SSEC", DataCategory.INDICES, "yahoo_indices", "000001.SS"),
                _instrument("STOXX50", DataCategory.INDICES, "yahoo_indices", "^STOXX50E"),
            ],
        ),'''

test_stocks = '''        ProviderCheckCase(
            name="yahoo_stocks",
            provider=YahooStocksProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "yahoo_stocks", "SBER.ME"),
                _instrument("LKOH", DataCategory.STOCKS, "yahoo_stocks", "LKOH.ME"),
                _instrument("ROSN", DataCategory.STOCKS, "yahoo_stocks", "ROSN.ME"),
            ],
        ),'''

c = c.replace('        ProviderCheckCase(\n            name="stooq_goods",', test_goods + '\n        ProviderCheckCase(\n            name="stooq_goods",')
c = c.replace('        ProviderCheckCase(\n            name="stooq_indices",', test_indices + '\n        ProviderCheckCase(\n            name="stooq_indices",')
c = c.replace('        ProviderCheckCase(\n            name="tinkoff",', test_stocks + '\n        ProviderCheckCase(\n            name="tinkoff",')

with open('scripts/check_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(c)
