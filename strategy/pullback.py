import logging 
from utils.pip_utils import price_to_pips

class PullbackQualifier:
    def __init__(self, min_candles=2, max_candles=5, min_depth=0.3, max_depth=0.6, ema_buffer=1.5):
        self.min_candles = min_candles
        self.max_candles = max_candles
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.ema_buffer = ema_buffer

    def qualify(self, pb_candles, impulse, indicators):
        n = len(pb_candles)
        if not (self.min_candles <= n <= self.max_candles):
            # print(f"DEBUG PB: candle count {n} out of range")
            return False

        impulse_range = impulse["high"] - impulse["low"]
        if impulse_range == 0:
            return False

        if impulse["direction"] == "BUY":
            current_low = min(c["low"] for c in pb_candles)
            depth = (impulse["high"] - current_low) / impulse_range

            # Structure check: no new high during pullback
            if max(c["high"] for c in pb_candles) > impulse["high"]:
                logging.info(f"PB Qualification: new high during pullback")
                return False
        else:
            current_high = max(c["high"] for c in pb_candles)
            depth = (current_high - impulse["low"]) / impulse_range

            # Structure check: no new low during pullback
            if min(c["low"] for c in pb_candles) < impulse["low"]:
                return False

        if not (self.min_depth <= depth <= self.max_depth):
            logging.info(f"PB Qualification: depth {depth:.3f} out of range")
            return False

        # EMA Interaction
        ema = indicators.get("ema20")
        if ema:
            near_ema = False
            for c in pb_candles:
                # Touch
                if c["low"] <= ema <= c["high"]:
                    near_ema = True
                    break
                # Within buffer
                dist = min(abs(c["low"] - ema), abs(c["high"] - ema))
                if price_to_pips(dist) <= self.ema_buffer:
                    near_ema = True
                    break

            if not near_ema:
                logging.info(f"PB Qualification: not near EMA")
                return False

        # Body Behavior
        pb_avg_body = sum(abs(c["close"] - c["open"]) for c in pb_candles) / n
        if pb_avg_body >= 0.7 * impulse["avg_body"]:
            logging.info(f"PB Qualification: body behavior failed")
            return False

        return True