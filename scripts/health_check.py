import MetaTrader5 as mt5
import yaml
import sys
import os

# Configure UTF-8 encoding for standard output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mt5_adapter import MT5Adapter

def run_health_check():
    print("🔍 Starting Bot Health Check...")

    # 1. Check config file
    config_path = "config/settings.yaml"
    if not os.path.exists(config_path):
        print("❌ Error: config/settings.yaml not found!")
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    print("✅ Configuration file loaded.")

    # 2. Check MT5 Connection
    adapter = MT5Adapter()
    login = config['mt5'].get('login')
    password = config['mt5'].get('password')
    server = config['mt5'].get('server')
    magic = config['mt5'].get('magic', 701970)

    # Handle optional credentials or placeholders
    if login == 0 or login == 12345678 or not login:
        print("📡 Attempting to connect to active MT5 terminal...")
        login = password = server = None
    else:
        print(f"📡 Attempting to connect to {server} with account {login}...")

    if adapter.connect(login=login, password=password, server=server, magic=magic):
        print("✅ MT5 Connection successful.")

        # 3. Check Account Info
        account = adapter.get_account_info()
        if account:
            print(f"✅ Account {account['login']} verified.")
            print(f"💰 Balance: {account['balance']} {account['currency']}")
            print(f"📈 Equity: {account['equity']}")
            print(f"⚖️ Margin: {account['margin']}")
        else:
            print("❌ Error: Could not retrieve account information.")

        # 4. Check Symbol
        symbol = config['trading']['symbol']
        tick = adapter.get_tick(symbol)
        if tick:
            print(f"✅ Symbol {symbol} is available. Last Bid: {tick['bid']}")
        else:
            print(f"❌ Error: Symbol {symbol} not found or no market data.")

        adapter.shutdown()
    else:
        print("❌ Error: MT5 connection failed. Check your credentials and MT5 terminal.")

if __name__ == "__main__":
    run_health_check()
