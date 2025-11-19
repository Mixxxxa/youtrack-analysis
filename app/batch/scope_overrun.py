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


from numpy import mean, median

from youtrack.helper import YouTrackHelper
from youtrack.utils.duration import Duration
from youtrack.utils.query import SearchQueryBuilder

from ..settings import Settings
from .batch_shared import (
    BatchShortIssueInfo,
    validate_input_params,
    validate_dates,
    get_required_issue_fields,
    batch_output_transformer,
    process_issue_custom_fields,
    JSON
)


def overrun_filter(parsed: BatchShortIssueInfo) -> bool:
    return parsed.is_scope_overrun() or parsed.lost_scope()


def overrun_transformer(parsed: BatchShortIssueInfo, raw: JSON) -> JSON:
    ret = batch_output_transformer(parsed=parsed, raw=raw)
    scope_overrun = parsed.overrun
    can_calc_percent = parsed.has_timings() and parsed.scope.to_seconds() != 0
    perc = round((parsed.spent_time.to_seconds() / parsed.scope.to_seconds()) * 100, 2) if can_calc_percent else 0
    ret |= {
        'scope_overrun': scope_overrun.format_yt() if scope_overrun else 'N/A',
        'scope_overrun_value': scope_overrun.to_seconds() if scope_overrun else 0,
        'scope_overrun_perc_value': perc
    }
    return ret


def get_overrun_stats(input: JSON, output: JSON) -> JSON:
    overrun_durations_sec: list[int] = list()
    for i in output:
        current_value = int(i['scope_overrun_value'])
        if current_value > 0:
            overrun_durations_sec.append(current_value)

    return {
        'count_total': len(input),
        'count_scope_ok': len(input) - len(output),
        'count_scope_overrun': len(output),
        'mean_overrun': Duration.from_minutes(int(mean(overrun_durations_sec) / 60)).format_yt(),
        'median_overrun': Duration.from_minutes(int(median(overrun_durations_sec) / 60)).format_yt()
    }


async def get_batch_scope_overrun_data(translator, settings: Settings, project: str, components: list[str], begin: str, end: str):
    # Empty page
    if not project and len(components) == 0 and not begin and not end:
        return dict()

    # Input validation
    validate_input_params(yt_config=settings.yt_config,
                          project=project,
                          components=components)
    begin_date, end_date = validate_dates(begin=begin, end=end)

    # Getting data
    query = SearchQueryBuilder(project=project,
                               components=components,
                               resolve_date_begin=begin_date,
                               resolve_date_end=end_date,
                               only_started=True).Build()
    helper = YouTrackHelper(instance_url=settings.app_config.host,
                            api_key=settings.app_config.api_key)
    data = await helper.get_raw_issues_by_query(query=query,
                                                fields=get_required_issue_fields())
    dataset = {
        'entries': process_issue_custom_fields(json=data,
                                               app_config=settings.app_config,
                                               filter_func=overrun_filter,
                                               output_transformer_func=overrun_transformer),
        'query': query,
        'query_url': str(helper.get_issues_search_url(query))
    }
    if len(dataset['entries']):
        dataset |= {
            'stats': get_overrun_stats(input=data, output=dataset['entries'])
        }
    return {
        'dataset': dataset
    }
