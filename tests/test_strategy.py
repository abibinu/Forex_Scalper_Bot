import unittest
from strategy.trend import TrendAnalyzer
from strategy.impulse import ImpulseDetector
from strategy.pullback import PullbackQualifier
from strategy.structure import StructureMonitor
from strategy.entry import EntryTrigger
from risk.risk_engine import RiskEngine
from utils.pip_utils import pips_to_price

class TestStrategyModules(unittest.TestCase):
    def setUp(self):
        self.trend = TrendAnalyzer(ema_slope_threshold=1.5)
        self.impulse = ImpulseDetector(min_size=8, min_candles=5)
        self.pullback = PullbackQualifier(min_depth=0.3, max_depth=0.6)
        self.structure = StructureMonitor(ema_buffer_pips=1.0)
        self.entry = EntryTrigger(buffer_pips=0.3)
        self.risk = RiskEngine()

    def test_trend_qualify(self):
        candle = {"close": 1.1020, "high": 1.1025, "low": 1.1015, "index": 20}
        indicators = {"ema20": 1.1010, "ema20_slope": 0.0002}
        self.trend.update(candle)
        self.assertTrue(self.trend.qualify_uptrend(candle, indicators))

        candle = {"close": 1.0980, "high": 1.0985, "low": 1.0975, "index": 20}
        indicators = {"ema20": 1.0990, "ema20_slope": -0.0002}
        self.trend.update(candle)
        self.assertTrue(self.trend.qualify_downtrend(candle, indicators))

    def test_trend_hh_ll(self):
        for i in range(20):
            # Increase high every 5 candles to maintain HH requirement
            high = 1.1025 + (i // 5) * 0.0001
            candle = {"close": high - 0.0005, "high": high, "low": high - 0.0010, "index": i}
            indicators = {"ema20": high - 0.0015, "ema20_slope": 0.0002}
            self.trend.update(candle)
            res = self.trend.qualify_uptrend(candle, indicators)
            self.assertTrue(res, f"Failed at index {i} with high {high}")

    def test_impulse_detect(self):
        candles = []
        for i in range(5):
            candles.append({
                "open": 1.1000 + i*0.0002,
                "close": 1.1002 + i*0.0002,
                "high": 1.1003 + i*0.0002,
                "low": 1.1000 + i*0.0002,
                "index": i
            })
        res = self.impulse.detect(candles)
        self.assertIsNotNone(res)
        self.assertEqual(res["direction"], "BUY")
        self.assertGreaterEqual(res["size"], 8.0)

    def test_pullback_qualify(self):
        impulse = {"direction": "BUY", "high": 1.1010, "low": 1.1000, "avg_body": 0.0002}
        pb_candles = [
            {"open": 1.1010, "close": 1.10095, "high": 1.1010, "low": 1.1009},
            {"open": 1.1009, "close": 1.10085, "high": 1.1009, "low": 1.1007}
        ]
        indicators = {"ema20": 1.1007}
        self.assertTrue(self.pullback.qualify(pb_candles, impulse, indicators))

    def test_risk_calculations(self):
        self.risk.register_new_trade()
        self.assertEqual(self.risk.trades_this_session, 1)
        entry = 1.1010
        pb_extreme = 1.1005
        sl, tp = self.risk.calculate_sl_tp("BUY", entry, pb_extreme)
        expected_sl = pb_extreme - pips_to_price(0.5)
        self.assertAlmostEqual(sl, expected_sl, places=5)
        risk = entry - sl
        expected_tp = entry + (risk * 1.2)
        self.assertAlmostEqual(tp, expected_tp, places=5)
        actual_rr = (tp - entry) / (entry - sl)
        self.assertAlmostEqual(actual_rr, 1.2, places=2)

if __name__ == "__main__":
    unittest.main()
