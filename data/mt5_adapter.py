import MetaTrader5 as mt5
from datetime import datetime
import logging


class MT5Adapter:
    def __init__(self, magic=701970):
        self.connected = False
        self.magic = magic

    def connect(self, login=None, password=None, server=None, magic=None) -> bool:
        if magic is not None:
            self.magic = magic

        if login and password and server:
            logging.info(f"Attempting MT5 connection with login {login} on server {server}...")
            init_res = mt5.initialize(login=int(login), password=str(password), server=str(server))
        else:
            logging.info("Attempting MT5 connection to active terminal...")
            init_res = mt5.initialize()

        if not init_res:
            err = mt5.last_error()
            logging.error(f"MT5 initialize failed: {err}")

            # Fallback: if credentials were provided but failed, try connecting to active terminal
            if login and password and server:
                logging.info("Falling back to active terminal connection...")
                if mt5.initialize():
                    self.connected = True
                    logging.info("MT5 connected successfully to active terminal")
                    return True
            return False

        self.connected = True
        logging.info("MT5 connected successfully")
        return True

    def get_account_info(self):
        """Returns account information including margin and balance."""
        account_info = mt5.account_info()
        if account_info is None:
            logging.error(f"Failed to get account info: {mt5.last_error()}")
            return None

        return {
            "login": account_info.login,
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "margin_free": account_info.margin_free,
            "margin_level": account_info.margin_level,
            "leverage": account_info.leverage,
            "currency": account_info.currency
        }

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
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Order failed: {result.retcode} - {result.comment}")
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
            "magic": self.magic,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
