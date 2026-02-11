from datetime import datetime, time, timedelta, timezone  # ✅ FIXED: Added timezone import

def get_ist_time(dt=None):
    """
    Get IST (Indian Standard Time) from a given datetime or current time.
    IST is UTC + 5:30
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # If dt is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone(timedelta(hours=5, minutes=30)))

def is_session_active(dt=None) -> bool:
    """
    Check if given datetime (or current time) falls within tradeable sessions.
    
    Trading Sessions (IST):
    - London: 12:30 - 16:30
    - New York: 18:30 - 21:30
    """
    now_ist = get_ist_time(dt).time()

    london_start = time(12, 30)
    london_end = time(16, 30)

    ny_start = time(18, 30)
    ny_end = time(21, 30)

    is_london = london_start <= now_ist <= london_end
    is_ny = ny_start <= now_ist <= ny_end

    return is_london or is_ny