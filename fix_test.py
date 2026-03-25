with open('tests/integration/test_providers_live.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('''    async def test_yahoo_stocks_live(self, yahoo_stocks):
        instruments = [
            _instrument("SBER", DataCategory.STOCKS, "yahoo_stocks", "SBER.ME"),
            _instrument("LKOH", DataCategory.STOCKS, "yahoo_stocks", "LKOH.ME"),
            _instrument("ROSN", DataCategory.STOCKS, "yahoo_stocks", "ROSN.ME"),
        ]
        result = await yahoo_stocks.fetch(instruments)
        # SBER.ME on yahoo is stale, so it may actually return something but old
        # we will just ensure it doesn't crash
        assert isinstance(result, dict)

''', '')

c = c.replace('''@pytest.fixture
def yahoo_stocks(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy) -> YahooStocksProvider:
    return YahooStocksProvider(http_client, circuit_breaker, retry_policy)

''', '')

c = c.replace('YahooStocksProvider,', '')

with open('tests/integration/test_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(c)

with open('scripts/check_providers_live.py', 'r', encoding='utf-8') as f:
    c2 = f.read()

test_stocks = '''        ProviderCheckCase(
            name="yahoo_stocks",
            provider=YahooStocksProvider(http, CircuitBreaker("yahoo", 2, 5), retry),
            instruments=[
                _instrument("SBER", DataCategory.STOCKS, "yahoo_stocks", "SBER.ME"),
                _instrument("LKOH", DataCategory.STOCKS, "yahoo_stocks", "LKOH.ME"),
                _instrument("ROSN", DataCategory.STOCKS, "yahoo_stocks", "ROSN.ME"),
            ],
        ),
'''
c2 = c2.replace(test_stocks, '')
c2 = c2.replace('YahooStocksProvider,', '')
with open('scripts/check_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(c2)
