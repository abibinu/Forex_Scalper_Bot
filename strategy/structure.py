from utils.pip_utils import pips_to_price

class StructureMonitor:
    def __init__(self, ema_buffer_pips=1.0):
        self.ema_buffer_pips = ema_buffer_pips

    def is_setup_valid(self, setup, candle, indicators):
        direction = setup["direction"]
        ema = indicators.get("ema20")

        if direction == "UP":
            # Invalidate if lower low forms compared to the start of the setup/impulse or pullback low
            if candle["low"] < setup.get("invalidation_price", 0):
                return False

            # Close below EMA - buffer
            if ema and candle["close"] < ema - pips_to_price(self.ema_buffer_pips):
                return False
        else:
            # Invalidate if higher high forms
            if candle["high"] > setup.get("invalidation_price", float('inf')):
                return False

            # Close above EMA + buffer
            if ema and candle["close"] > ema + pips_to_price(self.ema_buffer_pips):
                return False

        return True
