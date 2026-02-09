import logging

class ExecutionEngine:
    def __init__(self, mt5_adapter):
        self.mt5 = mt5_adapter
        self.active_trades = {}  # ticket -> trade_info

    def execute_signal(self, signal, symbol, volume=0.1):
        direction = signal["direction"]
        sl = signal["sl"]
        tp = signal["tp"]
        entry_price = signal["entry_price"]

        logging.info(f"Executing {direction} signal for {symbol} at {entry_price}")
        ticket = self.mt5.place_market_order(symbol, direction, volume, sl, tp, "Volman Scalper")

        if ticket > 0:
            self.active_trades[ticket] = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "be_moved": False,
                "candles_held": 0,
                "result_registered": False
            }
            logging.info(f"Trade opened successfully. Ticket: {ticket}")
        else:
            logging.error(f"Failed to open trade for {symbol}")

        return ticket

    def update_candles_count(self):
        for ticket in self.active_trades:
            self.active_trades[ticket]["candles_held"] += 1

    def manage_trades(self, symbol, risk_engine):
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return

        # Check if any trades were closed by SL/TP
        for ticket, trade in list(self.active_trades.items()):
            if not self.mt5.position_exists(ticket):
                logging.info(f"Trade {ticket} closed by SL/TP or manually.")
                if not trade["result_registered"]:
                    risk_engine.register_trade_result(win=False)
                    trade["result_registered"] = True
                del self.active_trades[ticket]
                continue

        for ticket, trade in list(self.active_trades.items()):
            current_price = tick["bid"] if trade["direction"] == "UP" else tick["ask"]

            # 1. Check Break-Even
            if not trade["be_moved"]:
                if risk_engine.should_move_to_be(trade["direction"], trade["entry_price"], current_price):
                    if self.mt5.modify_sl(ticket, trade["entry_price"]):
                        trade["be_moved"] = True
                        logging.info(f"Moved trade {ticket} to break-even")

            # 2. Check Time Stop (15 candles)
            if trade["candles_held"] >= 15:
                logging.info(f"Time stop reached for trade {ticket}. Closing position.")
                if self.mt5.close_position(ticket):
                    if not trade["result_registered"]:
                        risk_engine.register_trade_result(win=False)
                        trade["result_registered"] = True
                    del self.active_trades[ticket]
                    continue

    def cleanup_closed_trades(self, risk_engine):
        pass
