import youtrack as yt
from datetime import datetime,timedelta

def test_business_hours():
    # пятница 12:50 (9:50UTC) -> понедельник 13:20 (10:20UTC)
    val = yt.WorkItem(name='test', 
                      timestamp=yt.Timestamp(datetime.fromisoformat('2025-04-04T09:50:00.000+00:00')),
                      duration=yt.Duration(duration=timedelta(days=3, minutes=30)),
                      state='test')
    duration = val.business_duration
    assert duration.to_timedelta() == timedelta(hours=8, minutes=10)
    assert duration.format_yt() == '1d 10m'
