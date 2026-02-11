import unittest
import logging
import sys
from strategy.strategy_engine import StrategyEngine
from risk.risk_engine import RiskEngine

class TestIntegration(unittest.TestCase):
    def test_full_signal_flow(self):
        risk = RiskEngine()
        strategy = StrategyEngine(risk, symbol="EURUSD")

        # 1. Simulate established uptrend and an impulse leg
        # Feed exactly 5 candles to trigger impulse detection
        impulse_high = 0
        from datetime import datetime
        for i in range(5):
            candle = {
                "open": 1.1000 + i*0.0002,
                "close": 1.1002 + i*0.0002,
                "high": 1.1003 + i*0.0002,
                "low": 1.1000 + i*0.0002,
                "index": i,
                "timestamp": datetime(2026, 1, 1, 13, 0)
            }
            impulse_high = candle["high"]
            indicators = {
                "ema20": 1.1000,
                "ema20_slope": 0.0002, # 2 pips
                "avg_range": 0.0003 # 3 pips
            }
            strategy.process_candle(candle, indicators)

        # After a strong impulse, state should be WAITING_PULLBACK
        self.assertEqual(strategy.state, "WAITING_PULLBACK")

        # 2. Simulate a healthy 3-candle pullback
        # impulse_high = 1.1003 + 4*0.0002 = 1.1011.
        # impulse_low = 1.1000. Range = 0.0011.
        # Depth 30% = 0.00033. Target low around 1.1011 - 0.0004 = 1.1007.

        for i in range(5, 8):
            candle = {
                "open": 1.1007,
                "close": 1.1007,
                "high": 1.1008,
                "low": 1.1007,
                "index": i,
                "timestamp": datetime(2026, 1, 1, 13, 5)
            }
            # Keep price near EMA
            indicators = {
                "ema20": 1.1006,
                "ema20_slope": 0.00016, # 1.6 pips
                "avg_range": 0.0003
            }
            strategy.process_candle(candle, indicators)

        # If qualified, state moves to WAITING_TRIGGER
        self.assertEqual(strategy.state, "WAITING_TRIGGER")

        # 3. Simulate breakout trigger
        trigger_price = strategy.current_setup["trigger_price"]
        candle = {
            "open": trigger_price,
            "close": trigger_price + 0.0005,
            "high": trigger_price + 0.0005,
            "low": trigger_price - 0.0001,
            "index": 8,
            "timestamp": datetime(2026, 1, 1, 13, 10)
        }
        indicators = {
            "ema20": 1.1006,
            "ema20_slope": 0.00016,
            "avg_range": 0.0003
        }
        signal = strategy.process_candle(candle, indicators)

        self.assertIsNotNone(signal)
        self.assertEqual(signal["direction"], "BUY")
        self.assertIn("sl", signal)
        self.assertIn("tp", signal)
        self.assertGreater(signal["tp"], signal["entry_price"])
        self.assertLess(signal["sl"], signal["entry_price"])

if __name__ == "__main__":
    unittest.main()
