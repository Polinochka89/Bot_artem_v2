with open('tests/integration/test_providers_live.py', 'r', encoding='utf-8') as f:
    c = f.read()

imports_goods = '''from src.infrastructure.providers.goods import (
    AlphaVantageGoodsProvider,
    CbrGoodsProvider,
    StooqGoodsProvider,
    TwelveDataGoodsProvider,
    YahooGoodsProvider,
)'''
c = c.replace('from src.infrastructure.providers.goods import CbrGoodsProvider, StooqGoodsProvider', imports_goods)

imports_indices = '''from src.infrastructure.providers.indices import (
    AlphaVantageIndicesProvider,
    MoexIndicesProvider,
    StooqIndicesProvider,
    TwelveDataIndicesProvider,
    YahooIndicesProvider,
)'''
c = c.replace('from src.infrastructure.providers.indices import (\\n    AlphaVantageIndicesProvider,\\n    MoexIndicesProvider,\\n    StooqIndicesProvider,\\n    TwelveDataIndicesProvider,\\n)', imports_indices)

imports_stocks = '''from src.infrastructure.providers.stocks import (
    AlphaVantageStocksProvider,
    MoexStocksProvider,
    TinkoffProvider,
    TwelveDataStocksProvider,
    YahooStocksProvider,
)'''
c = c.replace('from src.infrastructure.providers.stocks import (\\n    AlphaVantageStocksProvider,\\n    MoexStocksProvider,\\n    TinkoffProvider,\\n    TwelveDataStocksProvider,\\n)', imports_stocks)

with open('tests/integration/test_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(c)
