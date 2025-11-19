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


from youtrack.entities import (
    WorkItem,
    count_working_minutes,
    get_workitem_duration,
    get_workitem_business_duration
)
from youtrack.utils.timestamp import Timestamp
from youtrack.utils.duration import Duration

from datetime import datetime, timedelta
import pytest


def test_business_hours():
    # пятница 12:50 (9:50UTC) -> понедельник 13:20 (10:20UTC)
    val = WorkItem(name='test',
                   timestamp=Timestamp(datetime.fromisoformat('2025-04-04T09:50:00.000+00:00')),
                   duration=Duration(duration=timedelta(days=3, minutes=30)),
                   state='test')
    duration = val.business_duration
    assert duration.to_timedelta() == timedelta(hours=8, minutes=10)
    assert duration.format_yt() == '1d 10m'


@pytest.mark.parametrize(
    'begin, end, expected', [
        (datetime.fromisoformat('2025-04-04T09:50:00.000+00:00'), datetime.fromisoformat('2025-04-04T09:50:00.000+00:00'), 0),    # The same time
        (datetime.fromisoformat('2025-04-04T06:00:00.000+00:00'), datetime.fromisoformat('2025-04-05T06:00:00.000+00:00'), 480),  # Whole day
        (datetime.fromisoformat('2025-04-03T06:50:00.000+00:00'), datetime.fromisoformat('2025-04-04T06:50:00.000+00:00'), 480),  # Whole day but with offset (to ensure that only left bound includes)
        (datetime.fromisoformat('2025-04-03T06:50:00.000+03:00'), datetime.fromisoformat('2025-04-04T06:50:00.000+03:00'), 480),  # Whole day with TZ and offset (to ensure that only left bound includes)
        (datetime.fromisoformat('2025-04-04T09:50:00.000+00:00'), datetime.fromisoformat('2025-04-05T09:50:00.000+00:00'), 250),  # Lunch and end of week
        (datetime.fromisoformat('2025-04-04T14:50:00.000+00:00'), datetime.fromisoformat('2025-04-07T10:10:00.000+00:00'), 250),  # Weekends + Lunch
    ]
)
def test_count_working_minutes(begin: datetime, end: datetime, expected: int):
    assert count_working_minutes(begin=begin, end=end) == expected


def test_sort():
    def create_workitem(timestamp: datetime, duration: timedelta) -> WorkItem:
        return WorkItem(timestamp=Timestamp(timestamp),
                        name='',
                        duration=Duration(duration=duration),
                        state='')

    # Friday 4 June -> Monday 7 June
    w1 = create_workitem(timestamp=datetime.fromisoformat('2025-06-04T12:30:00.000+00:00'),
                         duration=timedelta(days=1))
    assert w1.duration.format_yt() == '3d'
    assert w1.business_duration.format_yt() == '1d'

    # Monday 7 June 15:30 -> Monday 7 June 16:31
    w2 = create_workitem(timestamp=datetime.fromisoformat('2025-07-07T12:30:00.000+00:00'),
                         duration=timedelta(hours=1, minutes=1))
    assert w2.duration.format_yt() == '1h 1m'
    assert w2.business_duration.format_yt() == '1h 1m'

    # Monday 7 June 09:30 -> Monday 7 June 11:31
    w3 = create_workitem(timestamp=datetime.fromisoformat('2025-07-07T09:30:00.000+00:00'),
                         duration=timedelta(hours=3, minutes=1))
    assert w3.duration.format_yt() == '3h 1m'
    assert w3.business_duration.format_yt() == '2h 1m'  # -1h because lunch

    test_data = [w1, w2, w3]
    asc = [w2, w3, w1]
    desc = [w1, w3, w2]

    assert asc == sorted(test_data, key=get_workitem_duration)
    assert desc == sorted(test_data, key=get_workitem_duration, reverse=True)

    assert asc == sorted(test_data, key=get_workitem_business_duration)
    assert desc == sorted(test_data, key=get_workitem_business_duration, reverse=True)
