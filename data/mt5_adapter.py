import MetaTrader5 as mt5
from datetime import datetime
import logging


class MT5Adapter:
    def __init__(self):
        self.connected = False

    def connect(self) -> bool:
        if not mt5.initialize():
            logging.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False

        self.connected = True
        logging.info("MT5 connected successfully")
        return True

    def shutdown(self) -> None:
        mt5.shutdown()
        self.connected = False
        logging.info("MT5 shutdown")

    def get_tick(self, symbol: str):
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": tick.ask - tick.bid,
            "timestamp": datetime.fromtimestamp(tick.time)
        }

    def get_spread(self, symbol: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return float("inf")
        return tick.ask - tick.bid

    def place_market_order(
        self,
        symbol: str,
        direction: str,
        volume: float,
        sl: float,
        tp: float,
        comment: str = ""
    ) -> int:

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if direction == "BUY" else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 2,
            "magic": 701970,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Order failed: {result.retcode}")
            return -1

        return result.order

    def modify_sl(self, ticket: int, new_sl: float) -> bool:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False

        pos = position[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": pos.tp,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def position_exists(self, ticket: int) -> bool:
        position = mt5.positions_get(ticket=ticket)
        return position is not None and len(position) > 0

    def close_position(self, ticket: int) -> bool:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False

        pos = position[0]
        direction = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(pos.symbol).bid if direction == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(pos.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": direction,
            "price": price,
            "deviation": 2,
            "magic": 701970,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
