"""Calendar service: holiday-aware business day calculations and settlement delay estimation."""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import Holiday


# In-memory cache for holidays (loaded once from DB)
_holiday_cache: dict[tuple[date, str], bool] = {}


async def load_holidays(session: AsyncSession) -> None:
    """Load all holidays into memory cache."""
    global _holiday_cache
    result = await session.execute(select(Holiday))
    holidays = result.scalars().all()
    _holiday_cache = {(h.date, h.country): True for h in holidays}


def is_holiday(d: date, country: str) -> bool:
    return (d, country) in _holiday_cache


def is_business_day(d: date, country: str) -> bool:
    if d.weekday() >= 5:
        return False
    return not is_holiday(d, country)


def next_business_day(d: date, country: str) -> date:
    """Find the next business day on or after d."""
    while not is_business_day(d, country):
        d += timedelta(days=1)
    return d


def add_business_days(d: date, n: int, country: str) -> date:
    """Add n business days to date d."""
    added = 0
    current = d
    while added < n:
        current += timedelta(days=1)
        if is_business_day(current, country):
            added += 1
    return current


def days_to_next_holiday(d: date, country: str, max_lookahead: int = 30) -> int:
    """Return number of days until the next holiday (up to max_lookahead)."""
    for i in range(1, max_lookahead + 1):
        if is_holiday(d + timedelta(days=i), country):
            return i
    return max_lookahead


def business_day_index_in_month(d: date, country: str) -> int:
    """Return which business day of the month this is (1-indexed)."""
    count = 0
    current = date(d.year, d.month, 1)
    while current <= d:
        if is_business_day(current, country):
            count += 1
        current += timedelta(days=1)
    return count


def is_month_end_window(d: date, country: str, window: int = 3) -> bool:
    """Return True if d is within the last N business days of the month."""
    # Find last day of month
    if d.month == 12:
        last = date(d.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(d.year, d.month + 1, 1) - timedelta(days=1)

    # Count business days from d to end of month
    count = 0
    current = d
    while current <= last:
        if is_business_day(current, country):
            count += 1
        current += timedelta(days=1)

    return count <= window


CHANNEL_DELAYS = {
    "internal": {"typical": 1, "max": 4},
    "sepa": {"typical": 4, "max": 24},
    "swift": {"typical": 48, "max": 72},
    "card": {"typical": 24, "max": 120},
    "p2p": {"typical": 0, "max": 1},
    "partner": {"typical": 24, "max": 48},
}


def estimate_settlement_time(
    channel: str,
    source_country: str,
    target_country: str,
    initiated_date: date,
) -> tuple[date, date]:
    """Estimate typical and worst-case settlement dates.

    Returns (typical_date, worst_case_date).
    """
    delays = CHANNEL_DELAYS.get(channel, {"typical": 24, "max": 72})
    typical_hours = delays["typical"]
    max_hours = delays["max"]

    typical_days = max(1, typical_hours // 24)
    max_days = max(1, max_hours // 24)

    # Use the target country for business day calculation
    country = target_country

    typical_settle = add_business_days(initiated_date, typical_days, country)
    worst_settle = add_business_days(initiated_date, max_days, country)

    return typical_settle, worst_settle
