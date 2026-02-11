from utils.pip_utils import pips_to_price

class EntryTrigger:
    def __init__(self, buffer_pips=0.3):
        self.buffer_pips = buffer_pips

    def check_trigger(self, setup, candle):
        direction = setup["direction"]

        if direction == "BUY":
            trigger_price = setup["trigger_price"] + pips_to_price(self.buffer_pips)
            if candle["high"] >= trigger_price:
                return trigger_price
        else:
            trigger_price = setup["trigger_price"] - pips_to_price(self.buffer_pips)
            if candle["low"] <= trigger_price:
                return trigger_price

        return None
