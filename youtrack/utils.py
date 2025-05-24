import enum
import re
import datetime
import pandas as pd
import logging
from datetime import timezone,timedelta
from urllib.parse import urlparse,parse_qs


yt_logger = logging.getLogger("youtrack-analysis")


class InvalidIssueIdError(RuntimeError):
    def __init__(self, id: str, *args):
        super().__init__(f"Invalid issue id or url: '{id}'" , *args)

class ParsingError(RuntimeError):
    def __init__(self, id: str, message: str):
        super().__init__(f"Unable to parse data from issue '{id}': {message}")


class Duration:
    class FormatType(enum.Enum):
        YouTrack = enum.auto() # С днями, в дне 8 часов, обозначения сокращены до одной буквы 
        Business = enum.auto() # С днями, в дне 8 часов
        Natural = enum.auto()  # С днями, в дне 24 часа
        Hours = enum.auto()    # Только часы и минуты

    def __init__(self, duration: datetime.timedelta = datetime.timedelta()):
        self.__internal = duration

    def __lt__(self, other):
        if isinstance(other, Duration):
            return self.__internal < other.__internal
        if isinstance(other, datetime.timedelta):
            return self.__internal + other
        return NotImplemented
    
    def __eq__(self, other):
        if isinstance(other, Duration):
            return self.__internal == other.__internal
        if isinstance(other, datetime.timedelta):
            return self.__internal == other
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(self.__internal + other.__internal)
        if isinstance(other, datetime.timedelta):
            return Duration(self.__internal + other)
        return NotImplemented

    def __str__(self) -> str:
        return self.__format_impl(Duration.FormatType.Natural)
    
    def format_natural(self) -> str:
        return self.__format_impl(Duration.FormatType.Natural)
    
    def format_business(self) -> str:
        return self.__format_impl(Duration.FormatType.Business)
    
    def format_yt(self) -> str:
        return self.__format_impl(Duration.FormatType.YouTrack)
    
    def format_hours(self) -> str:
        return self.__format_impl(Duration.FormatType.Hours)
    
    def __format_impl(self, style: FormatType) -> str:
        res = ''
        total_sec = int(self.__internal.total_seconds())

        if total_sec == 0:
            return f'0m' if style == Duration.FormatType.YouTrack else '0 минут'
        
        def append_str(text: str):
            nonlocal res
            if len(res) > 0:
                res += ' '
            res += text
        
        SECONDS_IN_DAY: int = 86400
        SECONDS_IN_HOUR: int = 3600
        SECONDS_IN_MINUTE: int = 60
        SECONDS_IN_BUSINESS_DAY: int = SECONDS_IN_HOUR * 8

        if style != Duration.FormatType.Hours:
            divider = SECONDS_IN_DAY if style == Duration.FormatType.Natural else SECONDS_IN_BUSINESS_DAY
            if (days := total_sec // divider) != 0:
                total_sec -= days * divider
                append_str(f'{days}d' if style == Duration.FormatType.YouTrack else format_plural(days, ['день', 'дня', 'дней']))
        if (hours := total_sec // SECONDS_IN_HOUR) != 0:
            total_sec -= hours * SECONDS_IN_HOUR
            append_str(f'{hours}h' if style == Duration.FormatType.YouTrack else format_plural(hours, ['час', 'часа', 'часов']))
        if (minutes := total_sec // SECONDS_IN_MINUTE) != 0:
            append_str(f'{minutes}m' if style == Duration.FormatType.YouTrack else format_plural(minutes, ['минута', 'минуты', 'минут']))
        return res


    @staticmethod
    def from_minutes(value: int) -> 'Duration':
        """"""
        return Duration(datetime.timedelta(minutes=value))
    
    def to_timedelta(self) -> datetime.timedelta:
        return self.__internal
    
    def to_seconds(self) -> int:
        return int(self.__internal.total_seconds())
    

class UTC_BUSINESS_DAY:
    HOUR_BEGIN = 6
    HOUR_LUNCH_BEGIN = 10
    HOUR_LUNCH_END = 11
    HOUR_END = 15


class Timestamp:
    def __init__(self, datetime: datetime.datetime):
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
        if isinstance(other, datetime.timedelta):
            return Timestamp(self.__internal - other)
        if isinstance(other, Duration):
            return Timestamp(self.__internal - other.to_timedelta())
        return NotImplemented
    
    def __str__(self):
        timespec = '[%Y-%m-%dT%H:%M]'
        return self.__internal.strftime(timespec)
    
    def format_ru(self) -> str:
        return self.__internal.astimezone(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M') 

    @staticmethod
    def from_yt(timestamp_msec: str | int) -> 'Timestamp':
        assert isinstance(timestamp_msec, (int,str))
        return Timestamp(datetime.datetime.fromtimestamp(float(timestamp_msec) / 1000, tz=timezone.utc))
    
    @staticmethod
    def now() -> 'Timestamp':
        return Timestamp(datetime.datetime.now(tz=timezone.utc))
    
    def prev_second(self) -> 'Timestamp':
        """Берем предыдущую секунду, т.к. это не особо влияет на результат, но сильно облегчает визуальный дебаг"""
        return Timestamp(self.__internal - datetime.timedelta(seconds=1))
    
    @staticmethod
    def from_datetime(value: datetime.datetime) -> 'Timestamp':
        return Timestamp(datetime=value)

    def to_datetime(self, tz: timezone | None = None) -> datetime.datetime:
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
        temp = self.__internal - datetime.timedelta(days=days_to_shift)
        temp = temp.replace(hour=UTC_BUSINESS_DAY.HOUR_END, minute=0)
        return Timestamp(datetime=temp)
    
    def is_day_start(self) -> bool:
        return self.__internal.hour == UTC_BUSINESS_DAY.HOUR_BEGIN and self.__internal.minute == 0
    
    def is_monday(self) -> bool:
        return self.__internal.weekday() == 0
    

def format_plural(amount: int, variants: list[str]) -> str:
    assert len(variants) == 3
    amount = abs(amount)

    variant: int = 2
    if amount % 10 == 1 and amount % 100 != 11:
        variant = 0
    elif 2 <= amount % 10 <= 4 and (amount % 100 < 10 or amount % 100 >= 20):
        variant = 1

    return f'{amount} {variants[variant]}'


def is_working_hour(dt: pd.Timestamp) -> bool:
    """Функция проверки что timestamp входит в рабочее время"""
    if dt.weekday() >= 5:  # Суббота и Воскресенье
        return False
    return (dt.hour >= UTC_BUSINESS_DAY.HOUR_BEGIN and dt.hour < UTC_BUSINESS_DAY.HOUR_LUNCH_BEGIN) or (dt.hour >= UTC_BUSINESS_DAY.HOUR_LUNCH_END and dt.hour < UTC_BUSINESS_DAY.HOUR_END)


def count_working_minutes(begin: datetime.datetime, end: datetime.datetime) -> int:
    """Возвращает количество рабочих минут между двумя точками во времени"""
    time_index: pd.Timestamp = pd.date_range(start=pd.to_datetime(begin), 
                                             end=pd.to_datetime(end), 
                                             freq='min')
    return sum([is_working_hour(dt) for dt in time_index])


def is_empty(container) -> bool:
    return len(container) == 0

def str_to_bool(text: str|int) -> bool:
    return isinstance(text, (str,int)) and str(text).strip().lower() in ['true', '1']


def is_valid_issue_id(id: str) -> bool:
    issue_re = re.compile(r'^[a-z]+?-[0-9]+?$')
    return issue_re.match(id)
    

def extract_issue_id_from_url(url: str, host: str) -> str | None:
    try:
        parts = urlparse(url)
        if parts.scheme != 'https':
            return None
        if parts.hostname is None or parts.hostname != host:
            return None
        if parts.path is None or is_empty(parts.path):
            return None
        
        if parts.path.startswith('/youtrack/agiles/') and not is_empty(parts.query):
            query_parts = parse_qs(qs=parts.query)
            if 'issue' in query_parts and is_valid_issue_id(query_parts['issue'][0]):
                return query_parts['issue'][0]
            
        if parts.path.startswith('/youtrack/issue/'):
            path_parts = [s for s in str.split(parts.path, sep='/') if not is_empty(s.strip())]
            if len(path_parts) > 2 and is_valid_issue_id(path_parts[2]):
                return path_parts[2]
            
        if parts.path.startswith('/issue/'):
            path_parts = [s for s in str.split(parts.path, sep='/') if not is_empty(s.strip())]
            if len(path_parts) > 1 and is_valid_issue_id(path_parts[1]):
                return path_parts[1]
    except:
        pass
    return None


def issue_id_comparator(l: str, r: str) -> int:
    l_parts, r_parts = l.lower().split('-'), r.lower().split('-')
    assert len(l_parts) == 2 and len(r_parts) == 2 and l_parts[0].isascii() and r_parts[0].isascii()
    
    if l_parts[0] < r_parts[0]:
        return -1
    elif l_parts[0] > r_parts[0]:
        return 1
    else:
        l_num, r_num = int(l_parts[1]), int(r_parts[1])
        if l_num < r_num:
            return -1
        elif l_num > r_num:
            return 1
        else:
            return 0
        

def issue_id_to_key(id: str) -> tuple[str, int]:
    parts = id.lower().split('-')
    assert len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit()
    return (parts[0], int(parts[1]))