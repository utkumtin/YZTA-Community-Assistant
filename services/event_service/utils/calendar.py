"""Google Calendar URL olusturucu — API gerektirmez, URL semasi kullanir."""
from __future__ import annotations

from datetime import date, time, datetime, timedelta, timezone
from urllib.parse import quote


def build_google_calendar_url(
    title: str,
    event_date: date,
    event_time: time,
    duration_minutes: int,
    description: str = "",
    location: str = "",
) -> str:
    """Google Calendar 'Add Event' URL'i olusturur."""
    start_dt = datetime.combine(event_date, event_time, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    date_fmt = "%Y%m%dT%H%M%SZ"
    dates = f"{start_dt.strftime(date_fmt)}/{end_dt.strftime(date_fmt)}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates,
        "details": description,
        "location": location,
    }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items() if v)
    return f"https://calendar.google.com/calendar/render?{query}"
