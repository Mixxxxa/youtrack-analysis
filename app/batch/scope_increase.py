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


import aiohttp
from numpy import mean, median

from youtrack.utils.timestamp import Timestamp
from youtrack.utils.duration import Duration
from youtrack.utils.query import SearchQueryBuilder
from youtrack.utils.issue_state import IssueState
from youtrack.helper import YouTrackHelper
from youtrack.utils.anomalies import Anomaly, ScopeIncreasedAnomaly, ReopenAnomaly

from ..utils import logger
from ..settings import Settings, LocalSettings, ProjectSettings
from .batch_shared import (
    JSON,
    validate_input_params, 
    validate_dates,
    get_required_issue_fields,
    process_issue_custom_fields,
    batch_output_transformer
)


def get_anomalies(json, app_config: LocalSettings, project_short_name: str, current_state: str) -> list[Anomaly]:
    is_started = False
    resolved = False

    for entry in json:
        # Ищем изначальный state задачи
        if entry['$type'] == 'CustomFieldActivityItem' and entry['targetMember'] == '__CUSTOM_FIELD__State_2':
            is_started = IssueState.parse(entry['removed'][0]['name']).is_in_work()
            break
    else:
        # state не менялся — берём текущий
        is_started = IssueState.parse(current_state).is_in_work()
    
    ret: list[Anomaly] = []
    
    for entry in json:
        entry_type = entry['$type']
        project_local_settings = app_config.projects.get(project_short_name, None)
        default_scope = project_local_settings.default_values.scope if project_local_settings else None

        if entry_type == 'CustomFieldActivityItem':
            target_member = entry['targetMember']
            if target_member == '__CUSTOM_FIELD__State_2':
                new_state = IssueState.parse(entry['added'][0]['name'])
                if not is_started and new_state.is_in_work():
                    # С этого момента начинаем смотреть изменения Scope
                    is_started = True
                # Если задачу переоткрыли
                if resolved and new_state.is_active():
                    resolved = False
                    ret.append(ReopenAnomaly(timestamp=Timestamp.from_yt(entry['timestamp']), 
                                             responsible=entry['author']['name']))

            elif is_started and target_member == '__CUSTOM_FIELD__Estimation_19':
                before=Duration.from_minutes(entry['removed']) if entry['removed'] else default_scope
                after=Duration.from_minutes(entry['added']) if entry['added'] else default_scope
                
                # Нас интересует только увеличение
                if before < after:
                    ret.append(ScopeIncreasedAnomaly(timestamp=Timestamp.from_yt(entry['timestamp']), 
                                                     responsible=entry['author']['name'],
                                                     before=before,
                                                     after=after))
        elif entry_type == 'IssueResolvedActivityItem':
            resolved = True
    return ret


def has_scope_increase_anomaly(anomalies: list[Anomaly]) -> bool:
    return any(isinstance(i, ScopeIncreasedAnomaly) for i in anomalies)


def get_total_scope_increase(anomalies: list[Anomaly]) -> int:
    # Not using Duration to increase performance
    total_sec = 0
    for i in anomalies:
        if not isinstance(i, ScopeIncreasedAnomaly):
            continue
        delta = i.after.to_seconds() - i.before.to_seconds()
        if delta > 0:
            total_sec += delta
    return total_sec


async def get_batch_scope_increase_data(translator, settings: Settings, project: str, components: list[str], begin: str, end: str):
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
    context = {
        'dataset': {
            'entries': [],
            'query': query,
            'query_url': str(helper.get_issues_search_url(query))
        }
    }
    parsed = process_issue_custom_fields(json=data, 
                                         app_config=settings.app_config,
                                         output_transformer_func=batch_output_transformer)
    if len(parsed) == 0:
        return context
    
    activity_fields: list[str] = [
        'author(name)',
        'added(name)',
        'removed(name)',
        'timestamp',
        'targetMember'
    ]
    activities_categories: list[str] = [
        'CustomFieldCategory',
        'IssueResolvedCategory'
    ]

    increases_list = []
    async with aiohttp.ClientSession() as session:
        output: list[JSON] = context['dataset']['entries']
        for entry in parsed:
            # TODO Bad performance: rework to producer-consumer
            activities_data = await helper.get_issue_activities(session=session, 
                                                                issue_id=entry['id'],
                                                                fields=activity_fields,
                                                                categories=activities_categories)
            anomalies = get_anomalies(json=activities_data, 
                                        app_config=settings.app_config,
                                        project_short_name=entry['project_short_name'],
                                        current_state=entry['state'])
            total_increase_sec = get_total_scope_increase(anomalies)
            if total_increase_sec > 0:
                temp = {
                    'anomalies': [{ 'timestamp': i.timestamp.format_iso8601(), 
                                    'description': i.to_string(_=translator) } for i in anomalies],
                    'increased_total': Duration.from_minutes(total_increase_sec/60).format_yt(), 
                    'increased_total_value': total_increase_sec
                }
                temp |= entry
                increases_list.append(total_increase_sec)
                output.append(temp)

    if (dataset_size := len(context['dataset']['entries'])) > 0:
        context['dataset'] |= {
            'stats': {
                'count_total': len(parsed),
                'count_ok': len(parsed) - dataset_size,
                'count_fail': dataset_size,
                'mean_scope_increase': Duration.from_minutes(int(mean(increases_list) / 60)).format_yt(),
                'median_scope_increase': Duration.from_minutes(int(median(increases_list) / 60)).format_yt(),
            }
        }
    
    return context
