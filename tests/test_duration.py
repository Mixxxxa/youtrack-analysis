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


from youtrack.utils.duration import Duration, parse_duration_to_minutes
import datetime
import pytest


SECONDS_IN_DAY: int = 86400
SECONDS_IN_HOUR: int = 3600
SECONDS_IN_MINUTE: int = 60
SECONDS_IN_BUSINESS_DAY: int = SECONDS_IN_HOUR * 8


def test_from_minutes():
    # 2d 6h 15m
    value = (2 * SECONDS_IN_DAY + 6 * SECONDS_IN_HOUR + 15 * SECONDS_IN_MINUTE) / SECONDS_IN_MINUTE
    val = Duration.from_minutes(value=value)
    assert val.to_seconds() == value * 60


def test_format():
    value = Duration(datetime.timedelta(days=1, hours=1, minutes=1, seconds=1))
    assert value.format_yt() == '3d 1h 1m'
    assert value.format_yt_natural() == '1d 1h 1m'

    small_value = Duration(datetime.timedelta(seconds=45))
    assert small_value.format_yt() == '0m'
    assert small_value.format_yt_natural() == '0m'

    with pytest.raises(RuntimeError):
        str(value)
    # assert value.format_business() == '3 дня 1 час 1 минута'
    # assert value.format_natural() == natural_format
    # assert value.format_hours() == '25 часов 1 минута'


def test_compare():
    v500 = Duration.from_minutes(500)
    v500d = datetime.timedelta(minutes=500)
    v501 = Duration.from_minutes(501)
    v501d = datetime.timedelta(minutes=501)

    assert v500 == v500
    assert v500 == v500d

    assert v500 != v501
    assert v500 != v501d

    assert v500 < v501
    assert v500 < v501d

    assert v500 >= v500
    assert v500 >= v500d
    assert v501 >= v500
    assert v501 >= v500d


def test_calc():
    v500 = Duration.from_minutes(500)
    v502 = Duration.from_minutes(502)
    v1 = Duration.from_minutes(1)
    v1d = datetime.timedelta(minutes=1)

    assert (v500 + v1 + v1d) == v502
    assert (v502 - v1 - v1d) == v500


def test_zero():
    val = Duration()
    assert val.to_seconds() == 0
    assert val.format_yt() == '0m'
    assert val.format_yt_natural() == '0m'


@pytest.mark.parametrize(
    "s, expected",
    [
        ("1m", 1),
        ("15m", 15),
        ("1h", 60),
        ("2h", 120),
        ("1d", 8 * 60),                      # 1d = 8h
        ("1w", 5 * 8 * 60),                  # 1w = 5d = 40h
        ("1d 12h 15m", (8 + 12) * 60 + 15),  # 20h 15m = 1215
        ("1d12h15m", (8 + 12) * 60 + 15),
        ("  1D   2H   3M  ", (8 + 2) * 60 + 3),
        ("0w 0d 0h 0m", 0),
        ("0m", 0),
        ("0001h0002m", 62),
        ("1w1d2h3m", (5 * 8 + 1 * 8 + 2) * 60 + 3),
        ("3w", 3 * 5 * 8 * 60),
    ],
)
def test_valid_defaults(s, expected):
    assert parse_duration_to_minutes(s) == expected


def test_multiple_spaces_and_no_spaces():
    assert parse_duration_to_minutes("1d   2h") == (8 + 2) * 60
    assert parse_duration_to_minutes("1d2h") == (8 + 2) * 60


def test_custom_parameters():
    # hours_per_day=6, days_per_week=4
    # "1w 2d 3h 4m" => 1w=24h, 2d=12h, итого 39h 4m => 2340 + 4 = 2344
    assert parse_duration_to_minutes("1w 2d 3h 4m", hours_per_day=6, days_per_week=4) == 2344

    # Большие значения параметров тоже должны работать
    assert parse_duration_to_minutes("1d", hours_per_day=25) == 25 * 60
    assert parse_duration_to_minutes("1w", hours_per_day=10, days_per_week=10) == 100 * 60


@pytest.mark.parametrize(
    "bad",
    [
        "",          # пустая строка
        "   ",       # только пробелы
        "15",        # без единиц
        "h",         # без числа
        "1 h",       # пробел внутри сегмента не допускается
        "1.5h",      # дробные
        "-1h",       # отрицательные
        "1x",        # неизвестная единица
        "h1",        # неверный порядок
        "1h foo",    # мусор
        "10m__",     # мусор в конце
    ],
)
def test_invalid_raises(bad):
    with pytest.raises(ValueError):
        parse_duration_to_minutes(bad)


@pytest.mark.parametrize(
    "dup",
    [
        "1h 2h",
        "1H2h",
        "1w 1d 2h 3m 4m",
        "0m 0m",
    ],
)
def test_duplicates_raise(dup):
    with pytest.raises(ValueError):
        parse_duration_to_minutes(dup)


def test_parameter_validation():
    with pytest.raises(ValueError):
        parse_duration_to_minutes("1h", hours_per_day=0)
    with pytest.raises(ValueError):
        parse_duration_to_minutes("1h", days_per_week=0)
    with pytest.raises(ValueError):
        parse_duration_to_minutes("1h", hours_per_day=-1)
    with pytest.raises(ValueError):
        parse_duration_to_minutes("1h", days_per_week=-5)
    with pytest.raises(ValueError):
        parse_duration_to_minutes("1h", hours_per_day=8.5)  # не int
