from datetime import datetime, time, timedelta

def get_ist_time():
    # IST is UTC + 5:30
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def is_session_active() -> bool:
    now_ist = get_ist_time().time()

    london_start = time(12, 30)
    london_end = time(16, 30)

    ny_start = time(18, 30)
    ny_end = time(21, 30)

    is_london = london_start <= now_ist <= london_end
    is_ny = ny_start <= now_ist <= ny_end

    return is_london or is_ny
