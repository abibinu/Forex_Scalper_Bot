import logging
from data.tick_engine import TickCandleEngine
from indicators.indicator_engine import IndicatorEngine
from strategy.strategy_engine import StrategyEngine
from risk.risk_engine import RiskEngine
from execution.execution_engine import ExecutionEngine
from backtest.mock_adapter import MockMT5Adapter
from backtest.performance import PerformanceReport
from utils.pip_utils import price_to_pips

class ReplayEngine:
    def __init__(self, symbol="EURUSD"):
        self.symbol = symbol
        self.mock_mt5 = MockMT5Adapter()
        self.tick_engine = TickCandleEngine(70)
        self.ind_engine = IndicatorEngine()
        self.risk_engine = RiskEngine()
        self.strategy_engine = StrategyEngine(self.risk_engine)
        self.exec_engine = ExecutionEngine(self.mock_mt5)
        self.last_indicators = {}
        self.completed_trades = []
        logging.getLogger().setLevel(logging.INFO)

    def run(self, ticks):
        print(f"Starting backtest with {len(ticks)} ticks...")
        for tick in ticks:
            self.mock_mt5.set_tick(tick)
            closed = self.mock_mt5.check_sl_tp()
            for ticket, reason in closed:
                self._record_closed_trade(ticket, reason)
            if self.strategy_engine.state == "WAITING_TRIGGER":
                signal = self.strategy_engine.process_tick(tick, self.last_indicators)
                if signal: self._handle_signal(signal)
            candle = self.tick_engine.process_tick(tick)
            if candle:
                indicators = self.ind_engine.update(candle)
                self.last_indicators = indicators
                signal = self.strategy_engine.process_candle(candle, indicators)
                if signal: self._handle_signal(signal)
                self.exec_engine.update_candles_count()
            self.exec_engine.manage_trades(self.symbol, self.risk_engine)
            while self.exec_engine.closed_trades_history:
                ticket, trade = self.exec_engine.closed_trades_history.pop(0)
                self._record_closed_trade_from_history(ticket, trade)
        self._close_all_remaining()
        return PerformanceReport(self.completed_trades)

    def _handle_signal(self, signal):
        if self.risk_engine.can_trade():
            ticket = self.exec_engine.execute_signal(signal, self.symbol, 0.1)
            if ticket > 0: self.risk_engine.register_new_trade()

    def _record_closed_trade(self, ticket, reason):
        if ticket in self.exec_engine.active_trades:
            trade = self.exec_engine.active_trades[ticket]
            self._record_closed_trade_from_history(ticket, trade, reason)
            del self.exec_engine.active_trades[ticket]

    def _record_closed_trade_from_history(self, ticket, trade, reason=None):
        entry_price = trade["entry_price"]
        exit_price = self.mock_mt5.current_tick["bid"] if trade["direction"] == "UP" else self.mock_mt5.current_tick["ask"]
        if trade["direction"] == "UP": profit_pips = price_to_pips(exit_price - entry_price, self.symbol)
        else: profit_pips = price_to_pips(entry_price - exit_price, self.symbol)
        self.completed_trades.append({"ticket": ticket, "profit": profit_pips, "reason": reason or trade.get("exit_reason", "UNKNOWN"), "direction": trade["direction"]})

        # Only register if not already registered by ExecutionEngine
        if not trade.get("result_registered"):
            self.risk_engine.register_trade_result(win=(profit_pips > 0))

    def _close_all_remaining(self):
        for ticket in list(self.exec_engine.active_trades.keys()):
            self._record_closed_trade(ticket, "END_OF_DATA")
