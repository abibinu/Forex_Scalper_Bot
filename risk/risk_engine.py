from utils.pip_utils import pips_to_price, price_to_pips

class RiskEngine:
    def __init__(self, max_trades_session=5, max_consecutive_losses=3):
        self.max_trades_session = max_trades_session
        self.max_consecutive_losses = max_consecutive_losses
        self.trades_this_session = 0
        self.consecutive_losses = 0

    def can_trade(self):
        if self.trades_this_session >= self.max_trades_session:
            return False
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        return True

    def calculate_sl_tp(self, direction, entry_price, pb_extreme):
        """
        Calculates SL and TP based on structural extremes with fallbacks.
        TP adjusted to 1.5 RR for better profitability in 2026 conditions.
        """
        if direction == "BUY":
            sl = pb_extreme - pips_to_price(0.5)
            # If risk is too small (< 4 pips), use fallback (6.5 pips)
            if price_to_pips(entry_price - sl) < 4.0:
                sl = entry_price - pips_to_price(6.5)

            risk = entry_price - sl
            tp = entry_price + (risk * 1.5)  # Increased from 1.2
        else:
            sl = pb_extreme + pips_to_price(0.5)
            # If risk is too small (< 4 pips), use fallback (6.5 pips)
            if price_to_pips(sl - entry_price) < 4.0:
                sl = entry_price + pips_to_price(6.5)

            risk = sl - entry_price
            tp = entry_price - (risk * 1.5)  # Increased from 1.2

        return sl, tp

    def should_move_to_be(self, direction, entry_price, current_price):
        """
        Moves SL to BE when profit reaches 7.0 pips.
        Increased from 5.0 to allow more 'breathing room' for the 1.5 RR target.
        """
        if direction == "BUY":
            profit_pips = price_to_pips(current_price - entry_price)
        else:
            profit_pips = price_to_pips(entry_price - current_price)

        return profit_pips >= 7.0

    def register_new_trade(self):
        self.trades_this_session += 1

    def register_trade_result(self, win: bool):
        if win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

    def reset_session(self):
        self.trades_this_session = 0
        self.consecutive_losses = 0
