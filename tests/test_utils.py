from datetime import datetime, timezone
from map.utils import dt_or_none


def test_valid_dt():
    value = "2020-01-06T20:09:54.234+00:00"
    assert dt_or_none(value) == datetime(
        year=2020, month=1, day=6, hour=20, minute=9, second=54,
        microsecond=234000, tzinfo=timezone.utc)


def test_empty_safe():
    assert dt_or_none("") is None


def test_none_safe():
    assert dt_or_none(None) is None
