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


import pandas as pd
import datetime as dt


class UTC_BUSINESS_DAY_CONSTANTS:
    """Константы времени работы

    #TODO Вынести в конфиг
    """
    HOUR_BEGIN = 6
    HOUR_LUNCH_BEGIN = 10
    HOUR_LUNCH_END = 11
    HOUR_END = 15


def is_working_hour(dt: pd.Timestamp) -> bool:
    """Функция проверки что timestamp входит в рабочее время"""
    if dt.weekday() >= 5:  # Суббота и Воскресенье
        return False
    return (dt.hour >= UTC_BUSINESS_DAY_CONSTANTS.HOUR_BEGIN and dt.hour < UTC_BUSINESS_DAY_CONSTANTS.HOUR_LUNCH_BEGIN) or (dt.hour >= UTC_BUSINESS_DAY_CONSTANTS.HOUR_LUNCH_END and dt.hour < UTC_BUSINESS_DAY_CONSTANTS.HOUR_END)


def count_working_minutes(begin: dt.datetime, end: dt.datetime) -> int:
    """Возвращает количество рабочих минут между двумя точками во времени"""
    # Because date_range will create at least one element even if begin and end are equal
    if begin == end:
        return 0

    time_index: pd.Timestamp = pd.date_range(start=pd.to_datetime(begin),
                                             end=pd.to_datetime(end),
                                             freq='min',
                                             inclusive='left')
    return sum([is_working_hour(dt) for dt in time_index])


def is_next_day(current: dt.date, next: dt.date):
    return current + dt.timedelta(days=1) == next
