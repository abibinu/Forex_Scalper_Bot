from datetime import datetime, timedelta, timezone
import logging
import urllib.request
import xml.etree.ElementTree as ET
import json
import os

class NewsFilter:
    def __init__(self, buffer_minutes=15):
        self.buffer_minutes = buffer_minutes
        self.news_events = []

    def fetch_calendar(self, symbol="EURUSD"):
        """
        Fetches the weekly Forex Factory XML calendar.
        Filters for High/Medium impact events affecting the traded symbol's currencies.
        Caches results to a local JSON file to minimize network requests.
        """
        # Determine currencies from symbol
        symbol = symbol.upper()
        currencies = []
        for curr in ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']:
            if curr in symbol:
                currencies.append(curr)
        if not currencies:
            currencies = ['USD', 'EUR']  # Fallback

        cache_file = "data/news_events_cache.json"
        
        # Check cache (valid for 12 hours)
        if os.path.exists(cache_file):
            try:
                mtime = os.path.getmtime(cache_file)
                if datetime.now().timestamp() - mtime < 12 * 3600:
                    logging.info("Loading news events from cache...")
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        self.news_events = [datetime.fromisoformat(t) for t in data]
                    logging.info(f"Loaded {len(self.news_events)} news events from cache.")
                    return
            except Exception as e:
                logging.warning(f"Error reading news cache: {e}. Re-fetching...")

        logging.info(f"Fetching weekly calendar from Forex Factory RSS/XML feed for {currencies}...")
        url = "https://xml.forexfactory.com/forex_calendar_thisweek.xml"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            events = []
            for event in root.findall('event'):
                impact = event.find('impact')
                country = event.find('country')
                date = event.find('date')
                time_node = event.find('time')

                if impact is None or country is None or date is None or time_node is None:
                    continue

                impact_text = impact.text
                country_text = country.text
                date_text = date.text
                time_text = time_node.text

                # Filter by impact and country
                if impact_text not in ('High', 'Medium') or country_text not in currencies:
                    continue

                # Ignore all-day / tentative times
                if not time_text or time_text.lower() in ('day 1', 'day 2', 'day 3', 'all day', 'tentative'):
                    continue

                try:
                    dt_str = f"{date_text} {time_text.upper()}"
                    dt_naive = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
                    # Forex Factory calendar XML is set to Eastern Time (EST/EDT)
                    # Convert to UTC naive (add 5 hours)
                    dt_utc = dt_naive + timedelta(hours=5)
                    events.append(dt_utc)
                except Exception as ex:
                    logging.debug(f"Failed to parse news event time '{date_text} {time_text}': {ex}")

            self.news_events = sorted(list(set(events)))
            
            # Save cache
            with open(cache_file, 'w') as f:
                json.dump([t.isoformat() for t in self.news_events], f)

            logging.info(f"Successfully loaded and cached {len(self.news_events)} news events.")

        except Exception as e:
            logging.error(f"Failed to fetch Forex Factory calendar: {e}")
            # If fetch fails, try to load stale cache as fallback
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        self.news_events = [datetime.fromisoformat(t) for t in data]
                    logging.warning("Loaded stale news events from cache as fallback.")
                except Exception:
                    pass

    def is_news_active(self, current_time=None, broker_gmt_offset=0):
        if current_time is None:
            current_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            if current_time.tzinfo is not None:
                current_utc = current_time.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                current_utc = current_time - timedelta(hours=broker_gmt_offset)

        for event_time in self.news_events:
            start_block = event_time - timedelta(minutes=self.buffer_minutes)
            end_block = event_time + timedelta(minutes=self.buffer_minutes)
            if start_block <= current_utc <= end_block:
                return True
        return False

    def add_event(self, event_time):
        self.news_events.append(event_time)
