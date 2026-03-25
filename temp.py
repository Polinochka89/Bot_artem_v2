import yaml
with open('config/instruments.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
for ind in data['indices']:
    if ind['symbol'] == 'SPX':
        ind['ticker_map']['yahoo_indices'] = '^GSPC'
    if ind['symbol'] == 'SSEC':
        ind['ticker_map']['yahoo_indices'] = '000001.SS'
        ind['ticker_map']['stooq'] = '^SHC'
    if ind['symbol'] == 'STOXX50':
        ind['ticker_map']['yahoo_indices'] = '^STOXX50E'
for st in data['stocks']:
    if st['symbol'] == 'SBER':
        st['ticker_map']['yahoo_stocks'] = 'SBER.ME'
    if st['symbol'] == 'LKOH':
        st['ticker_map']['yahoo_stocks'] = 'LKOH.ME'
    if st['symbol'] == 'ROSN':
        st['ticker_map']['yahoo_stocks'] = 'ROSN.ME'
for g in data['goods']:
    if g['symbol'] == 'GOLD':
        g['ticker_map']['yahoo_goods'] = 'GC=F'
        g['ticker_map']['alphavantage_goods'] = 'GLD'
        g['ticker_map']['twelvedata_goods'] = 'XAU/USD'
    if g['symbol'] == 'OIL':
        g['ticker_map']['yahoo_goods'] = 'BZ=F'
        g['ticker_map']['alphavantage_goods'] = 'BNO'
        g['ticker_map']['twelvedata_goods'] = 'BNO'
with open('config/instruments.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
