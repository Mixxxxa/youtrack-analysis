import datetime
import enum

# TODO
# Нужно отрефакторить класс — сейчас совершенно непонятно что с чем складывается
# Изначально, парсер собирает его по схеме timestamp + минуты по yt
# в тестах зачастую хочется использовать логичный вариант timestamp + timedelta (как физических дней, но получается каша)
#TODO 2
# Duration должен строиться от двух datetime и отображать физический duration
class Duration:
    class FormatType(enum.Enum):
        YouTrack = enum.auto() # С днями, в дне 8 часов, обозначения сокращены до одной буквы (1d1h1m = 3d1h1m)
        YouTrackNatural = enum.auto() # С днями, в дне 24 часа, обозначения сокращены до одной буквы (1d1h1m = 1d1h1m)
        # TODO: кажется остальное не сильно и нужно...
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


    def __str__(self):
        raise RuntimeError('Use explicit variants instead')
    

    # def format_natural(self) -> str:
    #     return self.__format_impl(Duration.FormatType.Natural)
    

    # def format_business(self) -> str:
    #     return self.__format_impl(Duration.FormatType.Business)
    

    def format_yt(self) -> str:
        return self.__format_impl(Duration.FormatType.YouTrack)
    

    def format_yt_natural(self) -> str:
        return self.__format_impl(Duration.FormatType.YouTrackNatural)
    

    # def format_hours(self) -> str:
    #     return self.__format_impl(Duration.FormatType.Hours)
    

    def __format_impl(self, style: FormatType) -> str:
        res = ''
        total_sec = int(self.__internal.total_seconds())

        like_yt: bool = style in [Duration.FormatType.YouTrack, Duration.FormatType.YouTrackNatural]
        like_natural: bool = style in [Duration.FormatType.Natural, Duration.FormatType.YouTrackNatural]

        if total_sec < 60:
            # TODO check else branch
            return f'0m' if like_yt else '0 минут'
        
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
            divider = SECONDS_IN_DAY if like_natural else SECONDS_IN_BUSINESS_DAY
            if (days := total_sec // divider) != 0:
                total_sec -= days * divider
                #append_str(f'{days}d' if like_yt else format_plural(days, ['день', 'дня', 'дней']))
                append_str(f'{days}d')
        if (hours := total_sec // SECONDS_IN_HOUR) != 0:
            total_sec -= hours * SECONDS_IN_HOUR
            #append_str(f'{hours}h' if like_yt else format_plural(hours, ['час', 'часа', 'часов']))
            append_str(f'{hours}h')
        if (minutes := total_sec // SECONDS_IN_MINUTE) != 0:
            #append_str(f'{minutes}m' if like_yt else format_plural(minutes, ['минута', 'минуты', 'минут']))
            append_str(f'{minutes}m')
        return res


    @staticmethod
    def from_minutes(value: int) -> 'Duration':
        """"""
        return Duration(datetime.timedelta(minutes=value))
    

    def to_timedelta(self) -> datetime.timedelta:
        return self.__internal
    

    def to_seconds(self) -> int:
        """Количество секунд"""
        return int(self.__internal.total_seconds())
    
    