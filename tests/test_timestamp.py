from youtrack import Timestamp
from datetime import timedelta,datetime,timezone
from math import isclose


friday_end = datetime(year=2025, month=4, day=18, hour=15, minute=0, second=0, tzinfo=timezone.utc)
monday_begin = datetime(year=2025, month=4, day=21, hour=6, minute=0, second=0, tzinfo=timezone.utc)


def test_format_ru():
    val = Timestamp.from_datetime(friday_end)
    assert val.format_ru() == '18.04.2025 18:00'


def test_formats():
    val = Timestamp.from_datetime(friday_end)
    assert val.format_iso8601() == '2025-04-18T15:00+00:00'


def test_is_monday():
    assert Timestamp(friday_end).is_monday() == False
    assert Timestamp(monday_begin).is_monday() == True


def test_is_day_start():
    assert Timestamp(friday_end).is_day_start() == False
    assert Timestamp(monday_begin).is_day_start() == True


def test_prev():
    val = Timestamp.now()
    prev = val.prev_second()
    assert (val - timedelta(seconds=1)) == prev
    assert isclose(val.to_datetime().timestamp() - 1.0, prev.to_datetime().timestamp())


def test_to_end_of_previous_business_day():
    # Monday 9:00 -> Friday 18:00
    assert Timestamp(monday_begin).to_end_of_previous_business_day() == Timestamp(friday_end)

    # Saturday 12:40 -> Friday 18:00
    saturday_12_40 = datetime.fromisoformat('2025-04-19T12:40:00Z')
    assert Timestamp(saturday_12_40).to_end_of_previous_business_day() == Timestamp(friday_end)

    # Sunday 12:40 -> Friday 18:00
    sunday_12_40 = datetime.fromisoformat('2025-04-20T12:40:00Z')
    assert Timestamp(sunday_12_40).to_end_of_previous_business_day() == Timestamp(friday_end)

    # Wednesday 8:00 -> Tuesday 18:00
    wednesday_8_00 = datetime.fromisoformat('2025-04-16T08:00:00Z')
    tuesday_end = datetime.fromisoformat('2025-04-15T15:00:00Z')
    assert Timestamp(wednesday_8_00).to_end_of_previous_business_day() == Timestamp(tuesday_end)


def test_from_yt():
    val = Timestamp.from_yt('1733769636970')
    assert val.to_datetime() == datetime.fromisoformat('2024-12-09T18:40:36.970+00:00')
    assert val.format_ru() == '09.12.2024 21:40'


def test_off_by_one_sec():
    val1 = Timestamp(datetime.fromisoformat('2025-04-19T15:40:36.970+00:00'))
    val2 = val1.prev_second()
    diff = val2 - val1
    assert abs(diff.to_seconds()) == 1.0


def test_now():
    val = Timestamp.now()
    offset = val.to_datetime().tzinfo.utcoffset(None)
    assert offset is not None
    assert offset == timedelta()


def test_sub():
    val1 = Timestamp.now() # Should be with 
    val2 = Timestamp(datetime.fromisoformat('2024-04-19T15:40:36.970+00:00'))
    assert val1 - val2 # Test