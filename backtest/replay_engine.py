import logging
from data.tick_engine import TickCandleEngine
from indicators.indicator_engine import IndicatorEngine
from strategy.strategy_engine import StrategyEngine
from risk.risk_engine import RiskEngine
from execution.execution_engine import ExecutionEngine
from backtest.mock_adapter import MockMT5Adapter
from backtest.performance import PerformanceReport
from utils.pip_utils import price_to_pips, pips_to_price

class ReplayEngine:
    def __init__(self, symbol="EURUSD"):
        self.symbol = symbol
        self.mock_mt5 = MockMT5Adapter()
        self.tick_engine = TickCandleEngine(70)
        self.ind_engine = IndicatorEngine()
        self.risk_engine = RiskEngine()
        self.strategy_engine = StrategyEngine(self.risk_engine, symbol=self.symbol)
        self.exec_engine = ExecutionEngine(self.mock_mt5)
        self.last_indicators = {}
        self.completed_trades = []
        
        # Statistics tracking
        self.stats = {
            "ticks_processed": 0,
            "candles_formed": 0,
            "impulses_detected": 0,
            "pullbacks_qualified": 0,
            "triggers_waiting": 0,
            "trades_executed": 0,
            "structure_invalidations": 0
        }
        
        logging.getLogger().setLevel(logging.INFO)

    def run(self, ticks):
        print(f"Starting backtest with {len(ticks)} ticks...")
        
        for tick in ticks:
            self.stats["ticks_processed"] += 1
            
            # FIXED: Ensure spread exists and is reasonable
            if "spread" not in tick or tick["spread"] == 0 or tick["spread"] is None:
                if "bid" in tick and "ask" in tick and tick["ask"] > tick["bid"]:
                    tick["spread"] = tick["ask"] - tick["bid"]
                else:
                    # Default to 0.5 pips for backtest
                    tick["spread"] = pips_to_price(0.5, self.symbol)
            
            # FIXED: Ensure bid/ask exist
            if "bid" not in tick or tick["bid"] == 0:
                if "price" in tick:
                    tick["bid"] = tick["price"]
                else:
                    tick["bid"] = 1.1000  # Fallback
                    
            if "ask" not in tick or tick["ask"] == 0:
                tick["ask"] = tick["bid"] + tick["spread"]
            
            # Ensure timestamp
            if "timestamp" not in tick and "time" in tick:
                tick["timestamp"] = tick["time"]
            
            self.mock_mt5.set_tick(tick)
            
            # Check SL/TP hits
            closed = self.mock_mt5.check_sl_tp()
            for ticket, reason in closed:
                self._record_closed_trade(ticket, reason)
            
            # Process tick-level entries
            if self.strategy_engine.state == "WAITING_TRIGGER":
                self.stats["triggers_waiting"] += 1
                signal = self.strategy_engine.process_tick(tick, self.last_indicators)
                if signal: 
                    self._handle_signal(signal)
            
            # Process candles
            candle = self.tick_engine.process_tick(tick)
            if candle:
                self.stats["candles_formed"] += 1
                
                indicators = self.ind_engine.update(candle)
                self.last_indicators = indicators
                
                # Track state changes
                old_state = self.strategy_engine.state
                
                spread_pips = price_to_pips(tick["spread"], self.symbol)
                signal = self.strategy_engine.process_candle(candle, indicators, spread_pips=spread_pips)
                
                # Update statistics
                new_state = self.strategy_engine.state
                if old_state == "SEARCHING" and new_state == "WAITING_PULLBACK":
                    self.stats["impulses_detected"] += 1
                elif old_state == "WAITING_PULLBACK" and new_state == "WAITING_TRIGGER":
                    self.stats["pullbacks_qualified"] += 1
                elif old_state == "WAITING_TRIGGER" and new_state == "SEARCHING":
                    if not signal:  # If no signal, structure was invalidated
                        self.stats["structure_invalidations"] += 1
                
                if signal: 
                    self._handle_signal(signal)
                    
                self.exec_engine.update_candles_count()
            
            # Manage active trades
            self.exec_engine.manage_trades(self.symbol, self.risk_engine)
            
            # Process closed trades from execution engine
            while self.exec_engine.closed_trades_history:
                ticket, trade = self.exec_engine.closed_trades_history.pop(0)
                self._record_closed_trade_from_history(ticket, trade)
        
        # Close remaining positions
        self._close_all_remaining()
        
        # Print statistics
        self._print_statistics()
        
        return PerformanceReport(self.completed_trades)

    def _handle_signal(self, signal):
        if self.risk_engine.can_trade():
            ticket = self.exec_engine.execute_signal(signal, self.symbol, 0.1)
            if ticket > 0: 
                self.risk_engine.register_new_trade()
                self.stats["trades_executed"] += 1
                logging.info(f"✓ Trade #{self.stats['trades_executed']} executed: {signal['direction']} @ {signal['entry_price']:.5f}")

    def _record_closed_trade(self, ticket, reason):
        if ticket in self.exec_engine.active_trades:
            trade = self.exec_engine.active_trades[ticket]
            self._record_closed_trade_from_history(ticket, trade, reason)
            del self.exec_engine.active_trades[ticket]

    def _record_closed_trade_from_history(self, ticket, trade, reason=None):
        entry_price = trade["entry_price"]
        reason = reason or trade.get("exit_reason", "UNKNOWN")
        
        # Determine exit price based on reason
        if reason == "SL":
            exit_price = trade["sl"]
        elif reason == "TP":
            exit_price = trade["tp"]
        elif self.mock_mt5.current_tick:
            # For MARKET or TIME_STOP, use current tick price
            exit_price = self.mock_mt5.current_tick["bid"] if trade["direction"] == "BUY" else self.mock_mt5.current_tick["ask"]
        else:
            # Fallback to entry price if no tick available
            exit_price = entry_price
        
        if trade["direction"] == "BUY": 
            profit_pips = price_to_pips(exit_price - entry_price, self.symbol)
        else: 
            profit_pips = price_to_pips(entry_price - exit_price, self.symbol)
        
        self.completed_trades.append({
            "ticket": ticket, 
            "profit": profit_pips, 
            "reason": reason or trade.get("exit_reason", "UNKNOWN"), 
            "direction": trade["direction"]
        })

        # Only register if not already registered by ExecutionEngine
        if not trade.get("result_registered"):
            self.risk_engine.register_trade_result(win=(profit_pips > 0))

    def _close_all_remaining(self):
        for ticket in list(self.exec_engine.active_trades.keys()):
            self._record_closed_trade(ticket, "END_OF_DATA")
    
    def _print_statistics(self):
        print("\n" + "="*60)
        print("📈 BACKTEST STATISTICS")
        print("="*60)
        print(f"Ticks Processed:         {self.stats['ticks_processed']:,}")
        print(f"Candles Formed:          {self.stats['candles_formed']:,}")
        print(f"Impulses Detected:       {self.stats['impulses_detected']}")
        print(f"Pullbacks Qualified:     {self.stats['pullbacks_qualified']}")
        print(f"Structure Invalidations: {self.stats['structure_invalidations']}")
        print(f"Trades Executed:         {self.stats['trades_executed']}")
        
        if self.stats['impulses_detected'] > 0:
            pb_rate = self.stats['pullbacks_qualified'] / self.stats['impulses_detected'] * 100
            print(f"Pullback Conversion:     {pb_rate:.1f}%")
            
        if self.stats['pullbacks_qualified'] > 0:
            trade_rate = self.stats['trades_executed'] / self.stats['pullbacks_qualified'] * 100
            print(f"Trade Execution Rate:    {trade_rate:.1f}%")
            
        print("="*60 + "\n")