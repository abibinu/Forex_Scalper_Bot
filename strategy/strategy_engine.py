import logging
from strategy.trend import TrendAnalyzer
from strategy.impulse import ImpulseDetector
from strategy.pullback import PullbackQualifier
from strategy.structure import StructureMonitor
from strategy.entry import EntryTrigger
from utils.pip_utils import price_to_pips
from utils.news_filter import NewsFilter
from utils.time_utils import is_session_active

class StrategyEngine:
    def __init__(self, risk_engine, symbol="EURUSD"):
        self.symbol = symbol
        self.news_filter = NewsFilter()
        self.trend_analyzer = TrendAnalyzer()
        self.impulse_detector = ImpulseDetector()
        self.pullback_qualifier = PullbackQualifier()
        self.structure_monitor = StructureMonitor()
        self.entry_trigger = EntryTrigger()
        self.risk_engine = risk_engine

        self.candles = []
        self.state = "SEARCHING"
        self.current_setup = None

    def process_candle(self, candle, indicators, spread_pips=None):
        self.candles.append(candle)
        if len(self.candles) > 100:
            self.candles.pop(0)

        # Update trend analyzer structure
        self.trend_analyzer.update(candle)

        # 0. Spread Filter (README Section 6)
        if spread_pips is not None and spread_pips > 0.8:
            return None

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
        # 0. News Filter
        timestamp = candle.get("timestamp_open") or candle.get("timestamp")
        if self.news_filter.is_news_active(timestamp):
            return None

        # 0.1 Session Filter (README Section 13)
        if not is_session_active(timestamp):
            return None

        # Qualify Trend
        uptrend = self.trend_analyzer.qualify_uptrend(candle, indicators)
        downtrend = self.trend_analyzer.qualify_downtrend(candle, indicators)

        if not uptrend and not downtrend:
            return None

        # Detect Impulse
        impulse = self.impulse_detector.detect(self.candles)
        if impulse:
            if (uptrend and impulse["direction"] == "BUY") or (downtrend and impulse["direction"] == "SELL"):
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
        trend_valid = self.trend_analyzer.qualify_uptrend(candle, indicators) if setup["direction"] == "BUY" else self.trend_analyzer.qualify_downtrend(candle, indicators)
        if not trend_valid:
            logging.info("Trend invalidated during pullback. Resetting.")
            self.reset_state()
            return None

        # Qualify Pullback
        if self.pullback_qualifier.qualify(setup["pb_candles"], setup["impulse"], indicators):
            logging.info(f"Pullback qualified for {setup['direction']} setup.")

            # Prepare trigger info
            if setup["direction"] == "BUY":
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

        elif len(setup["pb_candles"]) > self.pullback_qualifier.max_candles:
            logging.info(f"Pullback too long ({len(setup['pb_candles'])} candles). Resetting.")
            self.reset_state()

        return None

    def _handle_waiting_trigger(self, candle, indicators):
        setup = self.current_setup

        # Check structure integrity
        if not self.structure_monitor.is_setup_valid(setup, candle, indicators):
            logging.info("Structure invalidated. Resetting.")
            self.reset_state()
            return None

        return self._check_entry_trigger(candle, setup)

    def process_tick(self, tick, indicators):
        if self.state != "WAITING_TRIGGER" or not self.current_setup:
            return None

        # 0. Spread Filter (README Section 6)
        spread_pips = price_to_pips(tick["ask"] - tick["bid"], self.symbol)
        if spread_pips > 0.8:
            return None

        # 0.1 Session Filter
        if not is_session_active(tick["timestamp"]):
            return None

        setup = self.current_setup
        # Use bid/ask for more accurate execution (README Section 5/6)
        # BUY trigger: ask must break level
        # SELL trigger: bid must break level
        if setup["direction"] == "BUY":
            price = tick["ask"]
        else:
            price = tick["bid"]

        tick_candle = {"high": price, "low": price, "close": price}
        return self._check_entry_trigger(tick_candle, setup)

    def _check_entry_trigger(self, candle_or_tick, setup):
        entry_price = self.entry_trigger.check_trigger(setup, candle_or_tick)
        if entry_price:
            logging.info(f"Entry triggered at {entry_price}")
            sl, tp = self.risk_engine.calculate_sl_tp(setup["direction"], entry_price, setup["pb_extreme"])
            signal = {"direction": setup["direction"], "entry_price": entry_price, "sl": sl, "tp": tp}
            self.reset_state()
            return signal
        return None

    def reset_state(self):
        self.state = "SEARCHING"
        self.current_setup = None
