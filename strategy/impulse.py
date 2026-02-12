from utils.pip_utils import price_to_pips

class ImpulseDetector:
    def __init__(self, min_size=8, min_candles=5, min_body_dominance=0.6, max_overlap=0.3):
        self.min_size = min_size
        self.min_candles = min_candles
        self.min_body_dominance = min_body_dominance
        self.max_overlap = max_overlap

    def detect(self, candles):
        if len(candles) < self.min_candles:
            return None

        # Check the last n candles for impulse
        # We can iterate backwards to find the best impulse leg
        for n in range(self.min_candles, min(len(candles) + 1, 15)):
            leg = candles[-n:]

            open_price = leg[0]["open"]
            close_price = leg[-1]["close"]
            size_pips = abs(price_to_pips(close_price - open_price))

            if size_pips < self.min_size:
                continue

            high = max(c["high"] for c in leg)
            low = min(c["low"] for c in leg)
            total_range = high - low
            if total_range == 0: continue

            sum_bodies = sum(abs(c["close"] - c["open"]) for c in leg)
            body_dominance = sum_bodies / total_range

            if body_dominance < self.min_body_dominance:
                continue

            sum_ranges = sum(c["high"] - c["low"] for c in leg)
            overlap = (sum_ranges - total_range) / sum_ranges if sum_ranges > 0 else 1

            if overlap > self.max_overlap:
                continue

            direction = "BUY" if close_price > open_price else "SELL"

            # Additional check: Directional closes
            up_closes = sum(1 for c in leg if c["close"] > c["open"])
            down_closes = sum(1 for c in leg if c["close"] < c["open"])

            if direction == "BUY" and up_closes < n * 0.6: continue
            if direction == "SELL" and down_closes < n * 0.6: continue

            return {
                "direction": direction,
                "size": size_pips,
                "high": high,
                "low": low,
                "count": n,
                "avg_body": sum_bodies / n
            }

        return None
