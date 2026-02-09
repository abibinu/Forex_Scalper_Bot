def get_pip_value(symbol: str) -> float:
    if "JPY" in symbol:
        return 0.01
    if "XAU" in symbol:
        return 0.1  # IC Markets Gold pip is 0.1
    return 0.0001

def price_to_pips(price_diff: float, symbol: str = "EURUSD") -> float:
    return price_diff / get_pip_value(symbol)

def pips_to_price(pips: float, symbol: str = "EURUSD") -> float:
    return pips * get_pip_value(symbol)
