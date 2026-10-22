from datetime import datetime, timezone


def utc_now():
    """Return the current UTC time as a naive datetime for existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
