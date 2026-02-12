# 🌟 Beginner's Guide: Volman 70-Tick Scalper

Welcome! This guide is designed to help you understand, test, and run the Volman Scalping Bot, even if you have never used a trading bot before.

---

## 1. What is this Bot?
This bot is an automated "scalper." It looks for very fast trading opportunities on the EURUSD currency pair. It follows a famous strategy by **Bob Volman**, which focuses on:
- **Trend**: Only trading when the market is moving clearly up or down.
- **Impulse**: Waiting for a strong "jump" in price.
- **Pullback**: Waiting for a small "rest" (retracement) before the price continues.
- **Tick Break**: Entering the trade the exact millisecond the price starts moving again.

---

## 2. How to Test It (Backtesting)
Before risking real money, you should always test the bot. We have built a "flight simulator" for the bot called a Backtester. It uses fake data to show you how the bot works.

### Steps to Run a Test:
1.  **Open your terminal** (Command Prompt or PowerShell).
2.  **Type this command** and press Enter (this uses fake data for a quick test):
    ```bash
    python run_backtest.py --days 2 --source synthetic
    ```
3.  **To test with REAL history** (requires MetaTrader 5 on Windows):
    ```bash
    python run_backtest.py --days 7 --source mt5
    ```
4.  **Read the Results**: The bot will simulate the trading and print a report like this:
2.  **Type this command** and press Enter:
    ```bash
    python run_backtest.py
    ```
3.  **Read the Results**: The bot will simulate two days of trading and print a report like this:
    - **Win Rate**: How many trades were successful (Target: 60%+).
    - **Profit Factor**: If this is above 1.0, the bot is making more than it loses.
    - **Total Net Profit**: How many "pips" (points) the bot gained.

---

## 3. How to Run for Real (Live Trading)
To trade for real, you need two things: **Windows** and **MetaTrader 5 (MT5)**.

### Step A: Setup your Computer
1.  **Install MetaTrader 5** from your broker (e.g., IC Markets).
2.  **Install Python**: Download from python.org (Make sure to check the box "Add Python to PATH" during installation).
3.  **Install the "Parts"**: Open your terminal in this folder and type:
    ```bash
    pip install -r requirements.txt
    ```

### Step B: Setup MetaTrader 5
1.  **Login** to your trading account.
2.  **Enable Trading**: Click the "Algo Trading" button at the top (it must be **Green**).
3.  **Fix Settings**:
    - Go to `Tools -> Options -> Expert Advisors`.
    - Check the box: `Allow Algorithmic Trading`.
    - Check the box: `Allow DLL imports`.
4.  **Market Watch**: Ensure `EURUSD` is visible in the list on the left.

### Step C: Configuration
1.  **Open the folder** `config` and open the file `settings.yaml` with Notepad.
2.  **Enter your details**: Put your MT5 Account Number, Password, and Server name in the file.
3.  **Save the file**.

### Step D: Start the Bot
1.  **Open your terminal** in this folder.
2.  **Check Connection**: Type this to make sure everything is correct:
    ```bash
    python scripts/health_check.py
    ```
3.  **Run the Bot**: If the check above is green, type:
    ```bash
    python main.py
    ```
4.  **Watch it work**: You will see a **Dashboard** in the console showing your balance, margin, and what the bot is doing!

---

## 4. When does the Bot trade?
The bot is smart! It only trades when there is a lot of activity in the market.
- **London Session**: 12:30 PM to 4:30 PM (IST)
- **New York Session**: 6:30 PM to 9:30 PM (IST)
*If you run it outside these times, it will simply wait patiently.*

---

## 5. Safety Rules (Risk Management)
The bot has built-in safety features to protect your account:
- **Stop Loss**: Every trade has a "safety net." If the price goes against you, it exits automatically to prevent big losses.
- **Max Trades**: It only takes 5 trades per session.
- **Loss Limit**: If it loses 3 times in a row, it stops trading for the day to keep you safe.
- **News Filter**: It avoids trading during big economic news events.

---

## 6. Troubleshooting
- **"MT5 initialize failed"**: Make sure MetaTrader 5 is actually open on your computer.
- **"No trades happening"**: Check the time. Is the market open? Is it during the sessions listed above?
- **"ModuleNotFoundError"**: You forgot to run `pip install -r requirements.txt`.

---

**⚠️ FINAL WARNING**: Never trade with money you cannot afford to lose. Start with a **DEMO account** (fake money) for at least 2 weeks until you feel comfortable.
