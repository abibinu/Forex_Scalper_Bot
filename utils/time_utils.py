from datetime import datetime, time, timedelta, timezone  # ✅ FIXED: Added timezone import

def get_ist_time(dt=None, broker_gmt_offset=0):
    """
    Get IST (Indian Standard Time) from a given datetime or current time.
    IST is UTC + 5:30.
    If dt is provided as naive, we treat it as broker time and convert to UTC
    using broker_gmt_offset, then convert to IST.
    """
    if dt is None:
        dt_utc = datetime.now(timezone.utc)
    else:
        if dt.tzinfo is None:
            # Treat naive dt as broker time, convert to UTC
            dt_utc = (dt - timedelta(hours=broker_gmt_offset)).replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)

    return dt_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))

_cached_session_config = None

def is_session_active(dt=None, session_config=None, broker_gmt_offset=0) -> bool:
    """
    Check if given datetime (or current time) falls within tradeable sessions.
    
    Trading Sessions (IST):
    - London: 12:30 - 16:30
    - New York: 18:30 - 21:30
    """
    global _cached_session_config
    if session_config is None:
        if _cached_session_config is not None:
            session_config = _cached_session_config
        else:
            import os
            import yaml
            config_path = "config/settings.yaml"
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        cfg = yaml.safe_load(f)
                        _cached_session_config = cfg.get("sessions")
                        session_config = _cached_session_config
                except Exception:
                    pass

    if session_config is not None:
        use_filter = session_config.get("use_session_filter", True)
        if not use_filter:
            return True
        london_start_str = session_config.get("london", {}).get("start", "12:30")
        london_end_str = session_config.get("london", {}).get("end", "16:30")
        ny_start_str = session_config.get("new_york", {}).get("start", "18:30")
        ny_end_str = session_config.get("new_york", {}).get("end", "21:30")
    else:
        london_start_str, london_end_str = "12:30", "16:30"
        ny_start_str, ny_end_str = "18:30", "21:30"

    def parse_time(time_str):
        h, m = map(int, time_str.split(":"))
        return time(h, m)

    london_start = parse_time(london_start_str)
    london_end = parse_time(london_end_str)
    ny_start = parse_time(ny_start_str)
    ny_end = parse_time(ny_end_str)

    now_ist = get_ist_time(dt, broker_gmt_offset=broker_gmt_offset).time()

    is_london = london_start <= now_ist <= london_end
    is_ny = ny_start <= now_ist <= ny_end

    return is_london or is_ny