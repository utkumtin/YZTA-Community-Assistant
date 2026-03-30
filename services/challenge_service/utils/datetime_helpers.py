from datetime import datetime, timezone

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)