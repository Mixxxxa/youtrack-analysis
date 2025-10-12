# Copyright 2025 Mikhail Gelvikh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
import enum
from typing import Final
import re


def parse_duration_to_minutes(
    s: str,
    hours_per_day: int = 8,
    days_per_week: int = 5,
) -> int:
    """
    Преобразует строку-длительность в минуты.

    Правила:
    - Допустимые единицы: w (недели), d (дни), h (часы), m (минуты).
    - Регистр единиц не важен.
    - Сегменты: "<целое_число><unit>" без пробела внутри, сегменты могут разделяться
      пробелами или идти подряд, напр. "1d 2h", "1d2h".
    - Только целые неотрицательные числа (0 разрешен).
    - Дубликаты единиц запрещены (напр. "1h 2h" — ошибка).
    - Любая ошибка парсинга, мусор, неизвестные единицы — выбрасывается ValueError.
    - Пустая строка или строка из пробелов — ValueError.

    Параметры:
    - hours_per_day: количество часов в дне (> 0).
    - days_per_week: количество дней в неделе (> 0).

    Возвращает:
    - int: общее количество минут (0 допустимо).

    Исключения:
    - ValueError при любой проблеме.
    """
    if not isinstance(s, str):
        raise ValueError("Duration must be a string")
    s = s.strip()
    if not s:
        raise ValueError("Empty duration string")

    if not isinstance(hours_per_day, int) or hours_per_day <= 0:
        raise ValueError("hours_per_day must be a positive integer")
    if not isinstance(days_per_week, int) or days_per_week <= 0:
        raise ValueError("days_per_week must be a positive integer")

    # Предкомпилированные значения
    MIN_PER_HOUR: Final[int] = 60
    min_per_day: Final[int] = hours_per_day * MIN_PER_HOUR
    min_per_week: Final[int] = days_per_week * min_per_day

    # Разбор: идем по строке, пропуская пробелы между сегментами
    i = 0
    n = len(s)
    total_minutes = 0
    seen_units: set[str] = set()

    # Сегмент: одно или несколько десятичных чисел + одна буква из [wdhm], без пробела внутри
    token_re = re.compile(r"(?i)(\d+)([wdhm])")

    while i < n:
        # Пропускаем пробелы между сегментами
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break

        m = token_re.match(s, i)
        if not m:
            # Неизвестный символ/формат в текущей позиции — ошибка
            snippet = s[i:i + 16]
            raise ValueError(f"Invalid segment at position {i}: {snippet!r}")

        value = int(m.group(1))
        unit = m.group(2).lower()

        if unit in seen_units:
            raise ValueError(f"Duplicate unit: {unit}")
        seen_units.add(unit)

        if unit == "m":
            total_minutes += value
        elif unit == "h":
            total_minutes += value * MIN_PER_HOUR
        elif unit == "d":
            total_minutes += value * min_per_day
        elif unit == "w":
            total_minutes += value * min_per_week
        else:
            # Сюда не попадем из-за regex, но оставим на всякий случай
            raise ValueError(f"Unknown unit: {unit}")

        i = m.end()

    return total_minutes

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


    def __repr__(self) -> str:
        return self.format_yt()


    def __lt__(self, other):
        if isinstance(other, Duration):
            return self.__internal < other.__internal
        if isinstance(other, datetime.timedelta):
            return self.__internal < other
        return NotImplemented
    

    def __ge__(self, other):
        if isinstance(other, Duration):
            return self.__internal >= other.__internal
        if isinstance(other, datetime.timedelta):
            return self.__internal >= other
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
    

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Duration(self.__internal - other.__internal)
        if isinstance(other, datetime.timedelta):
            return Duration(self.__internal - other)
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
    

    @staticmethod
    def from_text(text: str) -> 'Duration':
        """"""
        return Duration(datetime.timedelta(minutes=parse_duration_to_minutes(s=text)))
    

    def to_timedelta(self) -> datetime.timedelta:
        return self.__internal
    

    def to_seconds(self) -> int:
        """Количество секунд"""
        return int(self.__internal.total_seconds())
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """
        Валидация: принимаем Duration (как есть) и строки формата YouTrack.
        JSON-сериализация: короткий YouTrack (format_yt()).
        Python-сериализация (model_dump(mode='python')): вернуть сам Duration.
        """
        from pydantic_core import core_schema as cs

        def validator(value):
            if isinstance(value, cls):
                return value
            if isinstance(value, str):
                minutes = parse_duration_to_minutes(value)
                return cls.from_minutes(minutes)
            raise TypeError('Duration must be a YouTrack duration string like "1w 2d 3h 4m"')

        return cs.no_info_plain_validator_function(
            validator,
            serialization=cs.plain_serializer_function_ser_schema(
                function=lambda v: v.format_yt(),
                info_arg=False,
                return_schema=cs.str_schema(),  # ИСПРАВЛЕНО: используем return_schema
                when_used='json',               # только при JSON-сериализации
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """
        JSON Schema: строка формата YouTrack.
        """
        json_schema = handler(core_schema)
        json_schema.update(
            type='string',
            pattern=r'^\s*(?:\d+[wdhmWDHM]\s*)+$',
            examples=['1w 2d 3h 4m', '2h 15m', '3d', '0m'],
            description='YouTrack duration string (w=weeks, d=days, h=hours, m=minutes); day=8h, week=5d; duplicates are not allowed.',
        )
        return json_schema
    