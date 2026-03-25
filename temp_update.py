import re
with open('scripts/check_providers_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports_goods = '''from src.infrastructure.providers.goods import (
    AlphaVantageGoodsProvider,
    CbrGoodsProvider,
    StooqGoodsProvider,
    TwelveDataGoodsProvider,
    YahooGoodsProvider,
)'''
content = re.sub(r'from src\.infrastructure\.providers\.goods import CbrGoodsProvider, StooqGoodsProvider', imports_goods, content)

imports_indices = '''from src.infrastructure.providers.indices import (
    AlphaVantageIndicesProvider,
    MoexIndicesProvider,
    StooqIndicesProvider,
    TwelveDataIndicesProvider,
    YahooIndicesProvider,
)'''
content = re.sub(r'from src\.infrastructure\.providers\.indices import \(\n(?:.*\n)*?\)', imports_indices, content)

imports_stocks = '''from src.infrastructure.providers.stocks import (
    AlphaVantageStocksProvider,
    MoexStocksProvider,
    TinkoffProvider,
    TwelveDataStocksProvider,
    YahooStocksProvider,
)'''
content = re.sub(r'from src\.infrastructure\.providers\.stocks import \(\n(?:.*\n)*?\)', imports_stocks, content)

with open('scripts/check_providers_live.py', 'w', encoding='utf-8') as f:
    f.write(content)
