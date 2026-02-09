import logging
from utils.pip_utils import price_to_pips

class TrendAnalyzer:
    def __init__(self, ema_slope_threshold=1.5):
        self.ema_slope_threshold = ema_slope_threshold
        self.highs = []
        self.lows = []

    def update_structure(self, candle):
        self.highs.append(candle["high"])
        self.lows.append(candle["low"])
        if len(self.highs) > 100:
            self.highs.pop(0)
            self.lows.pop(0)

    def qualify_uptrend(self, candle, indicators):
        self.update_structure(candle)
        ema = indicators.get("ema20")
        slope = indicators.get("ema20_slope")

        if ema is None or slope is None:
            return False

        # 1. Price above EMA
        if candle["close"] <= ema:
            logging.info(f"Trend Analysis: Price {candle['close']} <= EMA {ema}")
            return False

        # 2. EMA sloping upward
        slope_pips = price_to_pips(slope)
        if slope_pips < self.ema_slope_threshold:
            logging.info(f"Trend Analysis: Slope {slope_pips:.2f} < Threshold {self.ema_slope_threshold}")
            return False

        # 3. Higher highs present (at least one HH in last 10 candles vs previous 10)
        if len(self.highs) >= 20:
            recent_max_high = max(self.highs[-10:])
            previous_max_high = max(self.highs[-20:-10])
            if recent_max_high <= previous_max_high:
                logging.info(f"Trend Analysis: No Higher High in recent 10 candles ({recent_max_high:.5f} <= {previous_max_high:.5f})")
                return False

        return True

    def qualify_downtrend(self, candle, indicators):
        self.update_structure(candle)
        ema = indicators.get("ema20")
        slope = indicators.get("ema20_slope")

        if ema is None or slope is None:
            return False

        # 1. Price below EMA
        if candle["close"] >= ema:
            logging.info(f"Trend Analysis: Price {candle['close']} >= EMA {ema}")
            return False

        # 2. EMA sloping downward
        slope_pips = price_to_pips(slope)
        if slope_pips > -self.ema_slope_threshold:
            logging.info(f"Trend Analysis: Slope {slope_pips:.2f} > -Threshold {self.ema_slope_threshold}")
            return False

        # 3. Lower lows present
        if len(self.lows) >= 20:
            recent_min_low = min(self.lows[-10:])
            previous_min_low = min(self.lows[-20:-10])
            if recent_min_low >= previous_min_low:
                logging.info(f"Trend Analysis: No Lower Low in recent 10 candles ({recent_min_low:.5f} >= {previous_min_low:.5f})")
                return False

        return True
