import logging
from utils.pip_utils import price_to_pips, pips_to_price

class TrendAnalyzer:
    def __init__(self, ema_slope_threshold=1.0):
        self.ema_slope_threshold = ema_slope_threshold
        self.highs = []
        self.lows = []

    def update_structure(self, candle):
        self.highs.append(candle["high"])
        self.lows.append(candle["low"])
        if len(self.highs) > 100:
            self.highs.pop(0)
            self.lows.pop(0)

    def update(self, candle):
        self.update_structure(candle)

    def qualify_uptrend(self, candle, indicators):
        ema = indicators.get("ema20")
        slope = indicators.get("ema20_slope")

        if ema is None or slope is None:
            return False

        # 1. Price above EMA (with 1.0 pip buffer to allow minor pierces)
        if candle["close"] < ema - pips_to_price(1.0):
            logging.debug(f"Trend Analysis: Price {candle['close']} < EMA {ema} - buffer")
            return False

        # 2. EMA sloping upward
        slope_pips = price_to_pips(slope)
        if slope_pips < self.ema_slope_threshold:
            logging.debug(f"Trend Analysis: Slope {slope_pips:.2f} < Threshold {self.ema_slope_threshold}")
            return False

        # 3. Higher highs present - FIXED LOGIC
        # Compare recent price vs earlier highs (not max vs max)
        if len(self.highs) >= 15:
            recent_high = self.highs[-1]  # Most recent high
            earlier_max = max(self.highs[-15:-5])  # Max from candles 5-15 ago
            
            if recent_high <= earlier_max:
                logging.debug(f"Trend Analysis: No Higher High ({recent_high:.5f} <= {earlier_max:.5f})")
                return False

        return True

    def qualify_downtrend(self, candle, indicators):
        ema = indicators.get("ema20")
        slope = indicators.get("ema20_slope")

        if ema is None or slope is None:
            return False

        # 1. Price below EMA (with 1.0 pip buffer)
        if candle["close"] > ema + pips_to_price(1.0):
            logging.debug(f"Trend Analysis: Price {candle['close']} > EMA {ema} + buffer")
            return False

        # 2. EMA sloping downward
        slope_pips = price_to_pips(slope)
        if slope_pips > -self.ema_slope_threshold:
            logging.debug(f"Trend Analysis: Slope {slope_pips:.2f} > -Threshold {self.ema_slope_threshold}")
            return False

        # 3. Lower lows present - FIXED LOGIC
        if len(self.lows) >= 15:
            recent_low = self.lows[-1]
            earlier_min = min(self.lows[-15:-5])
            
            if recent_low >= earlier_min:
                logging.debug(f"Trend Analysis: No Lower Low ({recent_low:.5f} >= {earlier_min:.5f})")
                return False

        return True