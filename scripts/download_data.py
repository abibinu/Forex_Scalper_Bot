import sys
import os
import argparse
from data.data_loader import DataLoader

def main():
    parser = argparse.ArgumentParser(description="Download historical tick data from MetaTrader 5")
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Symbol to download (default: EURUSD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to download (default: 1)")
    parser.add_argument("--output", type=str, default="data/historical_ticks.csv", help="Output file path")

    args = parser.parse_args()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    try:
        DataLoader.download_historical_ticks(
            symbol=args.symbol,
            days=args.days,
            output_file=args.output
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
