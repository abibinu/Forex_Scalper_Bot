import time
import logging
from datetime import datetime
from data.mt5_adapter import MT5Adapter
from data.tick_engine import TickCandleEngine
from indicators.indicator_engine import IndicatorEngine
from strategy.strategy_engine import StrategyEngine
from risk.risk_engine import RiskEngine
from execution.execution_engine import ExecutionEngine
from utils.time_utils import is_session_active
from utils.pip_utils import price_to_pips

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

class VolmanTradingBot:
    def __init__(self, symbol="EURUSD", volume=0.1):
        self.symbol = symbol
        self.volume = volume
        self.mt5 = MT5Adapter()
        self.tick_engine = None
        self.ind_engine = None
        self.risk_engine = None
        self.strategy_engine = None
        self.exec_engine = None
        self.last_indicators = {}
        self.last_tick_time = None
        self.connection_errors = 0
        self.max_connection_errors = 3
        self.session_start_time = None
        self.last_stats_log = None
        
    def ensure_mt5_connected(self):
        if not self.mt5.connected:
            logging.warning("⚠️ MT5 disconnected. Attempting reconnection...")
            for attempt in range(self.max_connection_errors):
                if self.mt5.connect():
                    logging.info("✅ MT5 reconnected successfully")
                    self.connection_errors = 0
                    return True
                time.sleep(5)
            return False
        return True
    
    def check_tick_heartbeat(self):
        if self.last_tick_time is None:
            return True
        time_since_last_tick = (datetime.now() - self.last_tick_time).total_seconds()
        if time_since_last_tick > 30:
            return False
        return True
    
    def log_statistics(self):
        logging.info("=" * 60)
        logging.info("📊 SESSION STATISTICS")
        logging.info(f"Symbol: {self.symbol}")
        logging.info(f"Trades this session: {self.risk_engine.trades_this_session}")
        logging.info(f"Strategy state: {self.strategy_engine.state}")
        logging.info("=" * 60)
    
    def initialize(self):
        if not self.mt5.connect():
            return False
        self.tick_engine = TickCandleEngine(70)
        self.ind_engine = IndicatorEngine()
        self.risk_engine = RiskEngine(max_trades_session=5, max_consecutive_losses=3)
        self.strategy_engine = StrategyEngine(self.risk_engine, symbol=self.symbol)
        self.exec_engine = ExecutionEngine(self.mt5)
        self.session_start_time = datetime.now()
        self.last_stats_log = datetime.now()
        return True
    
    def run(self):
        if not self.initialize():
            return
        try:
            iteration = 0
            while True:
                iteration += 1
                if iteration % 100 == 0:
                    self.ensure_mt5_connected()
                if (datetime.now() - self.last_stats_log).total_seconds() > 300:
                    self.log_statistics()
                    self.last_stats_log = datetime.now()
                if not is_session_active():
                    time.sleep(30)
                    continue
                try:
                    tick = self.mt5.get_tick(self.symbol)
                except:
                    tick = None
                if not tick:
                    time.sleep(0.1)
                    continue
                self.last_tick_time = datetime.now()
                spread_pips = price_to_pips(tick["spread"], self.symbol)
                if spread_pips > 0.8:
                    time.sleep(0.1)
                    continue

                if self.strategy_engine.state == "WAITING_TRIGGER":
                    signal = self.strategy_engine.process_tick(tick, self.last_indicators)
                    if signal:
                        self._handle_signal(signal)
                
                candle = self.tick_engine.process_tick(tick)
                if candle:
                    indicators = self.ind_engine.update(candle)
                    self.last_indicators = indicators
                    signal = self.strategy_engine.process_candle(candle, indicators, spread_pips=spread_pips)
                    if signal:
                        self._handle_signal(signal)
                    self.exec_engine.update_candles_count()
                self.exec_engine.manage_trades(self.symbol, self.risk_engine)
                time.sleep(0.001)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()
    
    def _handle_signal(self, signal):
        if self.risk_engine.can_trade():
            ticket = self.exec_engine.execute_signal(signal, self.symbol, self.volume)
            if ticket > 0:
                self.risk_engine.register_new_trade()

    def _shutdown(self):
        if self.mt5:
            self.mt5.shutdown()


def main():
    bot = VolmanTradingBot(symbol="EURUSD", volume=0.1)
    bot.run()

if __name__ == "__main__":
    main()
