import logging
from strategy.trend import TrendAnalyzer
from strategy.impulse import ImpulseDetector
from strategy.pullback import PullbackQualifier
from strategy.structure import StructureMonitor
from strategy.entry import EntryTrigger
from utils.pip_utils import price_to_pips

class StrategyEngine:
    def __init__(self, risk_engine):
        self.trend_analyzer = TrendAnalyzer()
        self.impulse_detector = ImpulseDetector()
        self.pullback_qualifier = PullbackQualifier()
        self.structure_monitor = StructureMonitor()
        self.entry_trigger = EntryTrigger()
        self.risk_engine = risk_engine

        self.candles = []
        self.state = "SEARCHING"
        self.current_setup = None

    def process_candle(self, candle, indicators):
        self.candles.append(candle)
        if len(self.candles) > 100:
            self.candles.pop(0)

        # 1. Volatility Filter
        avg_range = indicators.get("avg_range")
        if avg_range and price_to_pips(avg_range) < 0.6:
            if self.state != "SEARCHING":
                logging.info("Volatility dropped. Resetting state.")
                self.reset_state()
            return None

        # State Machine
        if self.state == "SEARCHING":
            return self._handle_searching(candle, indicators)

        elif self.state == "WAITING_PULLBACK":
            return self._handle_waiting_pullback(candle, indicators)

        elif self.state == "WAITING_TRIGGER":
            return self._handle_waiting_trigger(candle, indicators)

        return None

    def _handle_searching(self, candle, indicators):
        # Qualify Trend
        uptrend = self.trend_analyzer.qualify_uptrend(candle, indicators)
        downtrend = self.trend_analyzer.qualify_downtrend(candle, indicators)

        if not uptrend and not downtrend:
            return None

        # Detect Impulse
        impulse = self.impulse_detector.detect(self.candles)
        if impulse:
            if (uptrend and impulse["direction"] == "UP") or (downtrend and impulse["direction"] == "DOWN"):
                logging.info(f"Impulse detected: {impulse['direction']} size {impulse['size']:.1f} pips")
                self.current_setup = {
                    "impulse": impulse,
                    "direction": impulse["direction"],
                    "impulse_end_index": candle["index"],
                    "pb_candles": []
                }
                self.state = "WAITING_PULLBACK"
        return None

    def _handle_waiting_pullback(self, candle, indicators):
        setup = self.current_setup
        setup["pb_candles"].append(candle)

        # Check if trend still valid
        trend_valid = self.trend_analyzer.qualify_uptrend(candle, indicators) if setup["direction"] == "UP" else self.trend_analyzer.qualify_downtrend(candle, indicators)
        if not trend_valid:
            logging.info("Trend invalidated during pullback. Resetting.")
            self.reset_state()
            return None

        # Qualify Pullback
        if self.pullback_qualifier.qualify(setup["pb_candles"], setup["impulse"], indicators):
            logging.info(f"Pullback qualified for {setup['direction']} setup.")

            # Prepare trigger info
            if setup["direction"] == "UP":
                trigger_price = max(c["high"] for c in setup["pb_candles"])
                invalidation_price = min(c["low"] for c in setup["pb_candles"])
            else:
                trigger_price = min(c["low"] for c in setup["pb_candles"])
                invalidation_price = max(c["high"] for c in setup["pb_candles"])

            setup["trigger_price"] = trigger_price
            setup["invalidation_price"] = invalidation_price
            setup["pb_extreme"] = invalidation_price

            self.state = "WAITING_TRIGGER"
            setup["trigger_start_index"] = candle["index"]

        elif len(setup["pb_candles"]) > 5:
            logging.info("Pullback too long. Resetting.")
            self.reset_state()

        return None

    def _handle_waiting_trigger(self, candle, indicators):
        setup = self.current_setup

        # Check structure integrity
        if not self.structure_monitor.is_setup_valid(setup, candle, indicators):
            logging.info("Structure invalidated. Resetting.")
            self.reset_state()
            return None

        # Check for trigger
        entry_price = self.entry_trigger.check_trigger(setup, candle)
        if entry_price:
            logging.info(f"Entry triggered at {entry_price}")

            # Calculate SL/TP
            sl, tp = self.risk_engine.calculate_sl_tp(setup["direction"], entry_price, setup["pb_extreme"])

            signal = {
                "direction": setup["direction"],
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp
            }
            self.reset_state()
            return signal

        return None

    def reset_state(self):
        self.state = "SEARCHING"
        self.current_setup = None
