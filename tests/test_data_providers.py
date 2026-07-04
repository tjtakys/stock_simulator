from src.data.providers.yahoo import yahoo_symbol


def test_yahoo_symbol_appends_tokyo_suffix_for_japanese_codes():
    assert yahoo_symbol("285A") == "285A.T"
    assert yahoo_symbol("7203") == "7203.T"


def test_yahoo_symbol_keeps_explicit_suffix_or_us_ticker():
    assert yahoo_symbol("285A.T") == "285A.T"
    assert yahoo_symbol("AAPL") == "AAPL"
