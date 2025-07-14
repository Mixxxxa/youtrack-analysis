from datetime import datetime, timedelta, timezone
from .duration import Duration
from .timeutils import UTC_BUSINESS_DAY_CONSTANTS


class Timestamp:
    def __init__(self, datetime: datetime):
        self.__internal = datetime
        # Ensure that timestamp in UTC
        tz = self.__internal.timetz()
        assert tz is not None, 'Timestamp should contain timezone'
        assert tz.utcoffset() == timedelta(), 'Timestamp timezone should be in UTC'

    def __add__(self, other):
        if isinstance(other, Duration):
            return Timestamp(self.__internal + other.to_timedelta())
        return NotImplemented
    
    def __lt__(self, other):
        if isinstance(other, Timestamp):
            return self.__internal < other.__internal
        #if isinstance(other, datetime.datetime):
        #    return self.__internal + other
        return NotImplemented
    
    def __eq__(self, other):
        if isinstance(other, Timestamp):
            return self.__internal == other.__internal
        #if isinstance(other, datetime.datetime):
        #    return self.__internal + other
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Timestamp):
            return Duration(self.__internal - other.__internal)
        if isinstance(other, timedelta):
            return Timestamp(self.__internal - other)
        if isinstance(other, Duration):
            return Timestamp(self.__internal - other.to_timedelta())
        return NotImplemented
    
    def __str__(self):
        timespec = '[%Y-%m-%dT%H:%M]'
        return self.__internal.strftime(timespec)
    
    def format_ru(self) -> str:
        return self.__internal.astimezone(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M') 
    
    def format_iso8601(self) -> str:
        return self.__internal.isoformat(timespec='minutes')

    @staticmethod
    def from_yt(timestamp_msec: str | int) -> 'Timestamp':
        assert isinstance(timestamp_msec, (int,str))
        return Timestamp(datetime.fromtimestamp(float(timestamp_msec) / 1000, tz=timezone.utc))
    
    @staticmethod
    def now() -> 'Timestamp':
        return Timestamp(datetime.now(tz=timezone.utc))
    
    def prev_second(self) -> 'Timestamp':
        """Берем предыдущую секунду, т.к. это не особо влияет на результат, но сильно облегчает визуальный дебаг"""
        return Timestamp(self.__internal - timedelta(seconds=1))
    
    @staticmethod
    def from_datetime(value: datetime) -> 'Timestamp':
        return Timestamp(datetime=value)

    def to_datetime(self, tz: timezone | None = None) -> datetime:
        if tz is not None:
            return self.__internal.astimezone(tz)
        return self.__internal
    
    def to_end_of_previous_business_day(self) -> 'Timestamp':
        days_to_shift = 1
        match self.__internal.weekday():
            case 0: # Monday
                days_to_shift = 3
            case 6: # Sunday
                days_to_shift = 2
        temp = self.__internal - timedelta(days=days_to_shift)
        temp = temp.replace(hour=UTC_BUSINESS_DAY_CONSTANTS.HOUR_END, minute=0)
        return Timestamp(datetime=temp)
    
    def is_day_start(self) -> bool:
        return self.__internal.hour == UTC_BUSINESS_DAY_CONSTANTS.HOUR_BEGIN and self.__internal.minute == 0
    
    def is_monday(self) -> bool:
        return self.__internal.weekday() == 0