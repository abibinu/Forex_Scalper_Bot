from datetime import datetime

class MockTradeDeal:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockMT5Adapter:
    def __init__(self):
        self.connected = True
        self.current_tick = None
        self.positions = {}
        self.deals = {}
        self.next_ticket = 1000

    def connect(self):
        self.connected = True
        return True

    def shutdown(self):
        self.connected = False

    def get_tick(self, symbol):
        return self.current_tick

    def set_tick(self, tick):
        self.current_tick = tick

    def place_market_order(self, symbol, direction, volume, sl, tp, comment=""):
        ticket = self.next_ticket
        self.next_ticket += 1
        entry_price = self.current_tick["ask"] if direction == "BUY" else self.current_tick["bid"]
        self.positions[ticket] = {
            "symbol": symbol,
            "type": 0 if direction == "BUY" else 1,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "price": entry_price
        }
        # Add entry deal
        self.deals[ticket] = [
            MockTradeDeal(
                ticket=ticket,
                position_id=ticket,
                type=0 if direction == "BUY" else 1,
                entry=0, # ENTRY_IN
                price=entry_price,
                profit=0.0,
                volume=volume,
                time=int(datetime.now().timestamp())
            )
        ]
        return ticket

    def modify_sl(self, ticket, new_sl):
        if ticket in self.positions:
            self.positions[ticket]["sl"] = new_sl
            return True
        return False

    def position_exists(self, ticket):
        return ticket in self.positions

    def close_position(self, ticket):
        if ticket in self.positions:
            pos = self.positions[ticket]
            exit_price = self.current_tick["bid"] if pos["type"] == 0 else self.current_tick["ask"]
            profit = (exit_price - pos["price"]) if pos["type"] == 0 else (pos["price"] - exit_price)
            exit_deal = MockTradeDeal(
                ticket=ticket + 10000,
                position_id=ticket,
                type=1 if pos["type"] == 0 else 0,
                entry=1, # ENTRY_OUT
                price=exit_price,
                profit=profit,
                volume=pos["volume"],
                time=int(datetime.now().timestamp())
            )
            if ticket not in self.deals:
                self.deals[ticket] = []
            self.deals[ticket].append(exit_deal)
            del self.positions[ticket]
            return True
        return False

    def check_sl_tp(self):
        if not self.current_tick:
            return []
        closed_tickets = []
        bid = self.current_tick["bid"]
        ask = self.current_tick["ask"]
        for ticket, pos in list(self.positions.items()):
            if pos["type"] == 0:
                if bid <= pos["sl"]: closed_tickets.append((ticket, "SL", pos["sl"]))
                elif bid >= pos["tp"]: closed_tickets.append((ticket, "TP", pos["tp"]))
            else:
                if ask >= pos["sl"]: closed_tickets.append((ticket, "SL", pos["sl"]))
                elif ask <= pos["tp"]: closed_tickets.append((ticket, "TP", pos["tp"]))
        
        for ticket, reason, exit_price in closed_tickets:
            pos = self.positions[ticket]
            profit = (exit_price - pos["price"]) if pos["type"] == 0 else (pos["price"] - exit_price)
            exit_deal = MockTradeDeal(
                ticket=ticket + 10000,
                position_id=ticket,
                type=1 if pos["type"] == 0 else 0,
                entry=1,
                price=exit_price,
                profit=profit,
                volume=pos["volume"],
                time=int(datetime.now().timestamp())
            )
            if ticket not in self.deals:
                self.deals[ticket] = []
            self.deals[ticket].append(exit_deal)
            del self.positions[ticket]
            
        return [(ticket, reason) for ticket, reason, _ in closed_tickets]

    def get_position_outcome(self, ticket: int):
        if ticket in self.deals:
            deals = self.deals[ticket]
            total_profit = sum(d.profit for d in deals)
            exit_deals = [d for d in deals if d.entry in (1, 2)]
            exit_price = exit_deals[-1].price if exit_deals else None
            return {
                "profit": total_profit,
                "exit_price": exit_price,
                "win": total_profit > 0
            }
        return None
