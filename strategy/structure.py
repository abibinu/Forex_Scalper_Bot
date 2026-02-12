import logging
from utils.pip_utils import pips_to_price, price_to_pips

class StructureMonitor:
    def __init__(self, ema_buffer_pips=1.0, structure_buffer_pips=1.5):
        """
        Structure monitoring with tuned settings for better profitability.
        
        Tuned from:
        - structure_buffer_pips: 5.0 → 1.5
        - ema_buffer_pips: 2.0 → 1.0
        
        Reason: Tightening structure prevents holding onto failing setups.
        A breach of the pullback extreme by more than 1.5 pips usually signals
        the end of the squeeze.
        """
        self.ema_buffer_pips = ema_buffer_pips
        self.structure_buffer_pips = structure_buffer_pips

    def is_setup_valid(self, setup, candle, indicators):
        direction = setup["direction"]
        ema = indicators.get("ema20")

        if direction == "BUY":
            # Add proper tolerance to structure invalidation
            base_invalidation = setup.get("invalidation_price", 0)
            tolerance = pips_to_price(self.structure_buffer_pips)
            invalidation = base_invalidation - tolerance
            
            if candle["low"] < invalidation:
                breach = price_to_pips(base_invalidation - candle["low"])
                logging.info(f"Structure broken: Low breached by {breach:.1f} pips")
                return False

            # Close below EMA - buffer
            if ema and candle["close"] < ema - pips_to_price(self.ema_buffer_pips):
                logging.info(f"Structure broken: Close {candle['close']:.5f} below EMA {ema:.5f}")
                return False
                
        else:  # SELL
            # Add proper tolerance
            base_invalidation = setup.get("invalidation_price", float('inf'))
            tolerance = pips_to_price(self.structure_buffer_pips)
            invalidation = base_invalidation + tolerance
            
            if candle["high"] > invalidation:
                breach = price_to_pips(candle["high"] - base_invalidation)
                logging.info(f"Structure broken: High breached by {breach:.1f} pips")
                return False

            # Close above EMA + buffer
            if ema and candle["close"] > ema + pips_to_price(self.ema_buffer_pips):
                logging.info(f"Structure broken: Close {candle['close']:.5f} above EMA {ema:.5f}")
                return False

        return True