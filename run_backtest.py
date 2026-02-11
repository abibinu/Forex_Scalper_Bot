import argparse
import logging
import sys
from backtest.replay_engine import ReplayEngine
from data.data_loader import DataLoader

def main():
    parser = argparse.ArgumentParser(description="Volman Bot Backtester")
    parser.add_argument("--days", type=int, default=2, help="Number of days to backtest (default: 2)")
    parser.add_argument("--source", type=str, choices=["csv", "mt5"], default="csv",
                        help="Data source: csv or mt5 (mt5 requires Windows)")
    parser.add_argument("--csv", type=str, default="data/sample_ticks.csv", help="Path to CSV file (if source=csv)")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to backtest")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.WARNING)

    ticks = []

    if args.source == "csv":
        try:
            ticks = DataLoader.load_from_csv(args.csv)
            # Filter by days if possible (optional enhancement)
        except Exception as e:
            print(f"Error loading CSV: {e}")
            sys.exit(1)

    elif args.source == "mt5":
        try:
            df = DataLoader.download_historical_ticks(symbol=args.symbol, days=args.days)
            if df is not None:
                ticks = DataLoader.convert_df_to_ticks(df)
            else:
                print("Failed to download data from MT5.")
                sys.exit(1)
        except Exception as e:
            print(f"Error downloading from MT5: {e}")
            sys.exit(1)

    if not ticks:
        print("No data available for backtest.")
        sys.exit(1)

    # Run backtest
    engine = ReplayEngine(symbol=args.symbol)
    report = engine.run(ticks)

    # Display results
    report.display()

if __name__ == "__main__":
    main()
