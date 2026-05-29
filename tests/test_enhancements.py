import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, time, timezone, timedelta
import io
import os
import json

from utils.news_filter import NewsFilter
from utils.time_utils import is_session_active, get_ist_time
from backtest.mock_adapter import MockMT5Adapter
from execution.execution_engine import ExecutionEngine
from risk.risk_engine import RiskEngine

class TestEnhancements(unittest.TestCase):
    def setUp(self):
        # Ensure data folder exists for caching
        os.makedirs("data", exist_ok=True)
        # Clean cache if any
        if os.path.exists("data/news_events_cache.json"):
            try:
                os.remove("data/news_events_cache.json")
            except Exception:
                pass

    def test_news_filter_xml_parsing(self):
        xml_data = """<weeklyevents>
            <event>
                <title>Core Retail Sales m/m</title>
                <country>USD</country>
                <date>05-24-2026</date>
                <time>8:30am</time>
                <impact>High</impact>
            </event>
            <event>
                <title>German Flash PMI</title>
                <country>EUR</country>
                <date>05-25-2026</date>
                <time>3:30am</time>
                <impact>Medium</impact>
            </event>
            <event>
                <title>Low Impact news</title>
                <country>USD</country>
                <date>05-25-2026</date>
                <time>10:00am</time>
                <impact>Low</impact>
            </event>
        </weeklyevents>"""

        # Mock urllib.request.urlopen
        mock_response = MagicMock()
        mock_response.read.return_value = xml_data.encode('utf-8')
        mock_response.__enter__.return_value = mock_response

        with patch('urllib.request.urlopen', return_value=mock_response):
            news_filter = NewsFilter(buffer_minutes=15)
            # Fetch for EURUSD (should load EUR and USD news)
            news_filter.fetch_calendar(symbol="EURUSD")

            # Check events loaded
            # High USD event: 05-24-2026 8:30am EST -> converted to UTC (+5 hrs) -> 05-24-2026 13:30
            # Medium EUR event: 05-25-2026 3:30am EST -> converted to UTC (+5 hrs) -> 05-25-2026 08:30
            # Low impact event is filtered out
            self.assertEqual(len(news_filter.news_events), 2)
            
            usd_event = datetime(2026, 5, 24, 13, 30)
            eur_event = datetime(2026, 5, 25, 8, 30)
            
            self.assertIn(usd_event, news_filter.news_events)
            self.assertIn(eur_event, news_filter.news_events)

            # Test cache file is created
            self.assertTrue(os.path.exists("data/news_events_cache.json"))

            # Test active news window (15 mins buffer)
            # 13:20 UTC (10 mins before event) should be active
            self.assertTrue(news_filter.is_news_active(current_time=datetime(2026, 5, 24, 13, 20), broker_gmt_offset=0))
            # 13:50 UTC (20 mins after event) should not be active
            self.assertFalse(news_filter.is_news_active(current_time=datetime(2026, 5, 24, 13, 50), broker_gmt_offset=0))

            # Test broker timezone offset translation
            # If broker is GMT+2, then 15:20 broker time = 13:20 UTC
            self.assertTrue(news_filter.is_news_active(current_time=datetime(2026, 5, 24, 15, 20), broker_gmt_offset=2))

    def test_timezone_aware_session_filter(self):
        # Dynamic session hours config
        session_config = {
            "use_session_filter": True,
            "london": {"start": "12:30", "end": "16:30"},
            "new_york": {"start": "18:30", "end": "21:30"}
        }

        # Let's test a time in London Session: 14:00 IST
        # 14:00 IST is 08:30 UTC
        # If broker is GMT+2, broker time is 10:30
        broker_time = datetime(2026, 5, 25, 10, 30)
        self.assertTrue(is_session_active(dt=broker_time, session_config=session_config, broker_gmt_offset=2))

        # Outside session (e.g. 17:30 IST -> 12:00 UTC -> 14:00 broker time)
        broker_time_outside = datetime(2026, 5, 25, 14, 0)
        self.assertFalse(is_session_active(dt=broker_time_outside, session_config=session_config, broker_gmt_offset=2))

        # Test use_session_filter = False
        session_config_disabled = {"use_session_filter": False}
        self.assertTrue(is_session_active(dt=broker_time_outside, session_config=session_config_disabled, broker_gmt_offset=2))

    def test_deal_history_outcome_tracking(self):
        mock_mt5 = MockMT5Adapter()
        exec_engine = ExecutionEngine(mock_mt5)
        risk_engine = RiskEngine()

        # Set up a tick
        mock_mt5.set_tick({"bid": 1.1000, "ask": 1.1005, "timestamp": datetime.now(), "spread": 0.0005})
        
        # Place buy order
        signal = {"direction": "BUY", "entry_price": 1.1005, "sl": 1.0990, "tp": 1.1025}
        ticket = exec_engine.execute_signal(signal, "EURUSD", volume=0.1)
        self.assertTrue(ticket > 0)
        self.assertTrue(mock_mt5.position_exists(ticket))

        # Close position with TP
        mock_mt5.set_tick({"bid": 1.1030, "ask": 1.1035, "timestamp": datetime.now(), "spread": 0.0005})
        
        # Check SL/TP closing via mock adapter
        closed = mock_mt5.check_sl_tp()
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0][0], ticket)
        self.assertEqual(closed[0][1], "TP")

        # Position should not exist in MT5 anymore
        self.assertFalse(mock_mt5.position_exists(ticket))

        # Outcome check
        outcome = mock_mt5.get_position_outcome(ticket)
        self.assertIsNotNone(outcome)
        self.assertTrue(outcome["win"])
        self.assertAlmostEqual(outcome["exit_price"], 1.1025)
        self.assertGreater(outcome["profit"], 0.0)

        # Execution Engine manage_trades should process this
        exec_engine.manage_trades("EURUSD", risk_engine)
        self.assertEqual(risk_engine.consecutive_losses, 0)
        self.assertEqual(len(exec_engine.active_trades), 0)
        self.assertEqual(len(exec_engine.closed_trades_history), 1)
        
        closed_trade = exec_engine.closed_trades_history[0][1]
        self.assertEqual(closed_trade["exit_reason"], "MARKET")
        self.assertAlmostEqual(closed_trade["exit_price"], 1.1025)

if __name__ == '__main__':
    unittest.main()
