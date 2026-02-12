import time
import logging
import yaml
import os
import signal
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from data.mt5_adapter import MT5Adapter
from data.tick_engine import TickCandleEngine
from indicators.indicator_engine import IndicatorEngine
from strategy.strategy_engine import StrategyEngine
from risk.risk_engine import RiskEngine
from execution.execution_engine import ExecutionEngine
from utils.time_utils import is_session_active
from utils.pip_utils import price_to_pips

def setup_logging(config):
    log_level = getattr(logging, config['logging']['level'].upper(), logging.INFO)
    log_file = config['logging']['log_file_path']
    backup_count = config['logging']['backup_count']

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Rotating File Handler
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=backup_count)
    file_handler.setFormatter(formatter)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Remove default handlers if any
    if logger.hasHandlers() and len(logger.handlers) > 2:
        logger.handlers = [file_handler, console_handler]

class VolmanTradingBot:
    def __init__(self, config=None, config_path="config/settings.yaml"):
        self.config_path = config_path
        if config:
            self.config = config
        else:
            self.config = self._load_config()

        self.symbol = self.config['trading']['symbol']
        self.volume = self.config['trading']['volume']
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
            logging.warning("[!] MT5 disconnected. Attempting reconnection...")
            for attempt in range(self.max_connection_errors):
                if self.mt5.connect():
                    logging.info("[OK] MT5 reconnected successfully")
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
        account = self.mt5.get_account_info()

        logging.info("=" * 60)
        logging.info("BOT DASHBOARD")
        if account:
            logging.info(f"Account: {account['login']} | Balance: {account['balance']} {account['currency']}")
            logging.info(f"Equity: {account['equity']} | Margin: {account['margin']} | Free: {account['margin_free']}")
            logging.info(f"Margin Level: {account['margin_level']}%")

        logging.info("-" * 30)
        logging.info(f"Symbol: {self.symbol}")
        logging.info(f"Strategy State: {self.strategy_engine.state}")
        logging.info(f"Active Trades: {len(self.exec_engine.active_trades)}")
        logging.info(f"Session Trades: {self.risk_engine.trades_this_session}/{self.risk_engine.max_trades_session}")
        logging.info(f"Consecutive Losses: {self.risk_engine.consecutive_losses}/{self.risk_engine.max_consecutive_losses}")

        if self.last_indicators:
            ema = self.last_indicators.get('ema', 0)
            slope = self.last_indicators.get('ema_slope', 0)
            logging.info(f"EMA: {ema:.5f} | Slope: {slope:.2f}")

        logging.info("=" * 60)
    
    def _load_config(self):
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def initialize(self):
        login = self.config['mt5'].get('login')
        password = self.config['mt5'].get('password')
        server = self.config['mt5'].get('server')

        if not self.mt5.connect(login=login, password=password, server=server):
            logging.error("Failed to connect to MT5 with provided credentials")
            return False

        # Use config values instead of hardcoded ones
        tick_count = self.config['trading'].get('tick_count', 70)
        max_trades = self.config['trading'].get('max_trades_session', 5)
        max_losses = self.config['trading'].get('max_consecutive_losses', 3)
        tp_multiplier = self.config['trading'].get('take_profit_multiplier', 1.5)

        self.tick_engine = TickCandleEngine(tick_count)
        self.ind_engine = IndicatorEngine()
        self.risk_engine = RiskEngine(max_trades_session=max_trades, max_consecutive_losses=max_losses, tp_multiplier=tp_multiplier)
        self.strategy_engine = StrategyEngine(self.risk_engine, symbol=self.symbol)
        self.exec_engine = ExecutionEngine(self.mt5)
        self.session_start_time = datetime.now()
        self.last_stats_log = datetime.now()
        return True
    
    def run(self):
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if not self.initialize():
            logging.critical("Failed to initialize bot. Exiting.")
            return

        logging.info(f"Bot initialized and running for {self.symbol}")
        self.log_statistics()

        try:
            iteration = 0
            while True:
                iteration += 1

                # Connection monitoring (every ~10 seconds assuming ~100ms per loop)
                if iteration % 100 == 0:
                    if not self.ensure_mt5_connected():
                         logging.error("Critical: MT5 Connection lost. Attempting to recover...")
                         time.sleep(10)
                         continue

                # Tick heartbeat
                if iteration % 500 == 0 and not self.check_tick_heartbeat():
                    logging.warning("No ticks received for 30s. Market might be closed or connection stale.")
                if (datetime.now() - self.last_stats_log).total_seconds() > 300:
                    self.log_statistics()
                    self.last_stats_log = datetime.now()
                if not is_session_active():
                    time.sleep(30)
                    continue
                try:
                    tick = self.mt5.get_tick(self.symbol)
                except Exception as e:
                    logging.error(f"Error fetching tick: {e}")
                    tick = None
                if not tick:
                    time.sleep(0.1)
                    continue
                self.last_tick_time = datetime.now()
                spread_pips = price_to_pips(tick["spread"], self.symbol)
                max_spread = self.config['trading'].get('max_spread_pips', 0.8)
                if spread_pips > max_spread:
                    time.sleep(0.1)
                    continue

                if self.strategy_engine.state == "WAITING_TRIGGER":
                    trade_sig = self.strategy_engine.process_tick(tick, self.last_indicators)
                    if trade_sig:
                        self._handle_signal(trade_sig)
                
                candle = self.tick_engine.process_tick(tick)
                if candle:
                    indicators = self.ind_engine.update(candle)
                    self.last_indicators = indicators
                    trade_sig = self.strategy_engine.process_candle(candle, indicators, spread_pips=spread_pips)
                    if trade_sig:
                        self._handle_signal(trade_sig)
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

    def _signal_handler(self, sig, frame):
        logging.info("Shutting down bot gracefully...")
        self._shutdown()
        sys.exit(0)

    def _shutdown(self):
        if self.mt5:
            logging.info("Closing MT5 connection...")
            self.mt5.shutdown()


def main():
    config_path = "config/settings.yaml"
    # Load config once and pass it to setup_logging and the bot
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found!")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    setup_logging(config)

    logging.info("Starting Volman 70 Tick Bot Production Edition")
    bot = VolmanTradingBot(config=config)
    bot.run()

if __name__ == "__main__":
    main()
