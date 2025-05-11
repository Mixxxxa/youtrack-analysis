import youtrack.utils as yt
import datetime


SECONDS_IN_DAY: int = 86400
SECONDS_IN_HOUR: int = 3600
SECONDS_IN_MINUTE: int = 60
SECONDS_IN_BUSINESS_DAY: int = SECONDS_IN_HOUR * 8


def test_from_minutes():
    # 2d 6h 15m
    value = (2 * SECONDS_IN_DAY + 6 * SECONDS_IN_HOUR + 15 * SECONDS_IN_MINUTE) / SECONDS_IN_MINUTE
    val = yt.Duration.from_minutes(value=value)
    assert val.to_seconds() == value * 60

def test_format():
    value = yt.Duration(datetime.timedelta(days=1, hours=1, minutes=1, seconds=1))
    natural_format = '1 день 1 час 1 минута'
    assert value.format_yt() == '3d 1h 1m'
    assert value.format_business() == '3 дня 1 час 1 минута'
    assert value.format_natural() == natural_format
    assert value.format_hours() == '25 часов 1 минута'
    assert str(value) == natural_format

def test_lt():
    assert yt.Duration.from_minutes(500) < yt.Duration.from_minutes(501)
    assert yt.Duration.from_minutes(500) < datetime.timedelta(minutes=501)

def test_add():
    assert (yt.Duration.from_minutes(500) + yt.Duration.from_minutes(1)).to_seconds() == 30060
    assert (yt.Duration.from_minutes(500) + datetime.timedelta(minutes=1)).to_seconds() == 30060

def test_zero():
    val = yt.Duration()
    assert val.to_seconds() == 0
    assert val.format_yt() == '0m'
    assert val.format_business() == '0 минут'
    assert val.format_hours() == '0 минут'
    assert val.format_natural() == '0 минут'
