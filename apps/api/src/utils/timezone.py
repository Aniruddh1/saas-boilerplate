"""
Timezone Utilities.

Golden Rules:
1. Database: Always store UTC
2. API: Return ISO 8601 with Z suffix (UTC)
3. Frontend: Browser auto-converts to local via Intl API

Frontend pattern (automatic - no config needed):
    // Browser auto-detects user's timezone
    const utcDate = new Date("2024-01-15T14:30:00Z");
    const local = utcDate.toLocaleString();  // Auto local

    // Or with Intl for more control
    new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short'
    }).format(utcDate);

Server-side conversion (only for emails, PDFs, cron):
    Use user.timezone field for these cases only.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# UTC constant
UTC = timezone.utc


# ============================================================
# CORE FUNCTIONS
# ============================================================

def utc_now() -> datetime:
    """
    Get current time in UTC (timezone-aware).

    Always use this instead of datetime.utcnow() which returns
    naive datetime.

    Usage:
        from src.utils.timezone import utc_now
        record.created_at = utc_now()
    """
    return datetime.now(UTC)


def to_utc(dt: datetime, source_tz: Optional[str] = None) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime to convert
        source_tz: Source timezone if dt is naive

    Usage:
        # From user input with known timezone
        utc_time = to_utc(user_input, "America/New_York")
    """
    if dt.tzinfo is None:
        if source_tz:
            dt = dt.replace(tzinfo=ZoneInfo(source_tz))
        else:
            dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def from_utc(dt: datetime, target_tz: str) -> datetime:
    """
    Convert UTC to target timezone.

    Only use for server-side rendering (emails, PDFs).
    Frontend should use browser's Intl API instead.

    Usage:
        # For email template
        local_time = from_utc(order.created_at, user.timezone)
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo(target_tz))


# ============================================================
# ISO 8601 (API FORMAT)
# ============================================================

def to_iso8601(dt: datetime) -> str:
    """
    Format as ISO 8601 with Z suffix.

    Standard API response format.
    Frontend converts automatically.

    Usage:
        iso = to_iso8601(record.created_at)
        # "2024-01-15T14:30:00Z"
    """
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso8601(iso_string: str) -> datetime:
    """
    Parse ISO 8601 string to UTC datetime.

    Handles:
    - "2024-01-15T14:30:00Z"
    - "2024-01-15T09:30:00-05:00"
    """
    if iso_string.endswith("Z"):
        iso_string = iso_string[:-1] + "+00:00"
    dt = datetime.fromisoformat(iso_string)
    return to_utc(dt)


# ============================================================
# SERVER-SIDE ONLY (Emails, PDFs, Cron)
# ============================================================

def format_for_user(dt: datetime, user_tz: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format UTC datetime in user's timezone.

    ONLY use for server-rendered content:
    - Email templates
    - PDF reports
    - Cron job logic

    NOT for API responses - let frontend handle display.

    Usage:
        # In email template
        formatted = format_for_user(
            order.created_at,
            user.timezone,
            "%B %d, %Y at %I:%M %p"
        )
    """
    local_dt = from_utc(dt, user_tz)
    return local_dt.strftime(fmt)


def start_of_day_utc(dt: datetime, user_tz: str) -> datetime:
    """
    Get start of day in user's timezone, as UTC.

    For date-range queries respecting user's day boundary.

    Usage:
        # "Today" in user's timezone
        today_start = start_of_day_utc(utc_now(), user.timezone)
        query.filter(Order.created_at >= today_start)
    """
    local_dt = from_utc(dt, user_tz)
    start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return to_utc(start)


def end_of_day_utc(dt: datetime, user_tz: str) -> datetime:
    """Get end of day in user's timezone, as UTC."""
    local_dt = from_utc(dt, user_tz)
    end = local_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return to_utc(end)


# ============================================================
# VALIDATION
# ============================================================

def is_valid_timezone(tz_name: str) -> bool:
    """Check if timezone name is valid IANA timezone."""
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False
