from datetime import datetime, timedelta, timezone

_offset_days = 0


def now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_offset_days)


def advance(days: int) -> datetime:
    global _offset_days
    _offset_days += days
    return now()


def reset() -> None:
    global _offset_days
    _offset_days = 0
