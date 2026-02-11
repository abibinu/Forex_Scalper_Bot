import pandas as pd
from datetime import datetime, timedelta
import logging
import os

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    logging.warning("MetaTrader5 package not found. Historical data download will be unavailable.")

class DataLoader:
    """
    Handles fetching and loading historical data for backtesting.
    """

    @staticmethod
    def download_historical_ticks(symbol, days=1, output_file=None):
        """
        Downloads historical tick data from MT5.
        Requires MT5 terminal to be running on Windows.
        """
        if mt5 is None:
            raise ImportError("MetaTrader5 package is required to download data.")

        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        logging.info(f"Downloading historical ticks for {symbol} (Last {days} days)...")

        utc_to = datetime.now()
        utc_from = utc_to - timedelta(days=days)

        # Requesting ticks
        ticks = mt5.copy_ticks_from(symbol, utc_from, mt5.COPY_TICKS_ALL)

        if ticks is None:
            logging.error(f"Failed to download ticks: {mt5.last_error()}")
            mt5.shutdown()
            return None

        mt5.shutdown()

        # Convert to DataFrame
        df = pd.DataFrame(ticks)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df['spread'] = df['ask'] - df['bid']

        if output_file:
            df.to_csv(output_file, index=False)
            logging.info(f"Data saved to {output_file}")

        return df

    @staticmethod
    def load_from_csv(csv_path):
        """
        Loads tick data from a CSV file.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        logging.info(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path)

        # Calculate spread if missing
        if 'spread' not in df.columns and 'bid' in df.columns and 'ask' in df.columns:
            df['spread'] = df['ask'] - df['bid']

        # Ensure timestamp is present
        if 'timestamp' not in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'])
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df.to_dict('records')

    @staticmethod
    def convert_df_to_ticks(df):
        """
        Converts a DataFrame of ticks into the list-of-dicts format
        used by the ReplayEngine.
        """
        return df.to_dict('records')
