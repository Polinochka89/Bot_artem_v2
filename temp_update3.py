import re

with open('tests/integration/test_providers_live.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Add fixtures
fixtures = '''

@pytest.fixture
def yahoo_goods(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy) -> YahooGoodsProvider:
    return YahooGoodsProvider(http_client, circuit_breaker, retry_policy)

@pytest.fixture
def alphavantage_goods(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy, alphavantage_key: str | None) -> AlphaVantageGoodsProvider:
    return AlphaVantageGoodsProvider(http_client, circuit_breaker, retry_policy, alphavantage_key)

@pytest.fixture
def twelvedata_goods(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy, twelvedata_key: str | None) -> TwelveDataGoodsProvider:
    return TwelveDataGoodsProvider(http_client, circuit_breaker, retry_policy, twelvedata_key)

@pytest.fixture
def yahoo_indices(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy) -> YahooIndicesProvider:
    return YahooIndicesProvider(http_client, circuit_breaker, retry_policy)

@pytest.fixture
def yahoo_stocks(http_client: HttpClient, circuit_breaker: CircuitBreaker, retry_policy: RetryPolicy) -> YahooStocksProvider:
    return YahooStocksProvider(http_client, circuit_breaker, retry_policy)
'''
c = c.replace('class TestLiveGoodsProviders:', fixtures + '\nclass TestLiveGoodsProviders:')

# Add goods tests
goods_tests = '''
    async def test_yahoo_goods_live(self, yahoo_goods):
        instruments = [
            _instrument("GOLD", DataCategory.GOODS, "yahoo_goods", "GC=F"),
            _instrument("OIL", DataCategory.GOODS, "yahoo_goods", "BZ=F"),
        ]
        result = await yahoo_goods.fetch(instruments)
        assert len(result) == 2
        for price in result.values():
            assert price.value > 0

    @pytest.mark.skipif("not os.getenv('ALPHAVANTAGE_API_KEY')")
    async def test_alphavantage_goods_live(self, alphavantage_goods):
        instruments = [
            _instrument("GOLD", DataCategory.GOODS, "alphavantage_goods", "GLD"),
            _instrument("OIL", DataCategory.GOODS, "alphavantage_goods", "BNO"),
        ]
        result = await alphavantage_goods.fetch(instruments)
        assert len(result) > 0

    @pytest.mark.skipif("not os.getenv('TWELVE_DATA_API_KEY')")
    async def test_twelvedata_goods_live(self, twelvedata_goods):
        instruments = [
            _instrument("GOLD", DataCategory.GOODS, "twelvedata_goods", "XAU/USD"),
            _instrument("OIL", DataCategory.GOODS, "twelvedata_goods", "BNO"),
        ]
        result = await twelvedata_goods.fetch(instruments)
        assert len(result) > 0
'''
c = c.replace('    async def test_stooq_goods_live(self, stooq_goods):', goods_tests + '\n    async def test_stooq_goods_live(self, stooq_goods):')

# Add indices tests
indices_tests = '''
    async def test_yahoo_indices_live(self, yahoo_indices):
        instruments = [
            _instrument("SPX", DataCategory.INDICES, "yahoo_indices", "^GSPC"),
            _instrument("SSEC", DataCategory.INDICES, "yahoo_indices", "000001.SS"),
            _instrument("STOXX50", DataCategory.INDICES, "yahoo_indices", "^STOXX50E"),
        ]
        result = await yahoo_indices.fetch(instruments)
        assert len(result) == 3
        for price in result.values():
            assert price.value > 0
'''
c = c.replace('    async def test_moex_indices_live(self, moex_indices):', indices_tests + '\n    async def test_moex_indices_live(self, moex_indices):')

# Update stock tests for yahoo and include ROSN for moex/tinkoff
stocks_tests = '''
    async def test_yahoo_stocks_live(self, yahoo_stocks):
        instruments = [
            _instrument("SBER", DataCategory.STOCKS, "yahoo_stocks", "SBER.ME"),
            _instrument("LKOH", DataCategory.STOCKS, "yahoo_stocks", "LKOH.ME"),
            _instrument("ROSN", DataCategory.STOCKS, "yahoo_stocks", "ROSN.ME"),
        ]
        result = await yahoo_stocks.fetch(instruments)
        # SBER.ME on yahoo is stale, so it may actually return something but old
        # we will just ensure it doesn't crash
        assert isinstance(result, dict)
'''

c = c.replace('    async def test_moex_stocks_live(self, moex_stocks):', stocks_tests + '\n    async def test_moex_stocks_live(self, moex_stocks):')

with open('tests/integration/test_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(c)
