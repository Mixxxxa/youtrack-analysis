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


from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Any, Callable

from youtrack.entities import Version
from youtrack.utils.duration import Duration
from youtrack.utils.anomalies import Anomaly
from youtrack.instance import YouTrackInstanceConfig

from .exceptions import BadQueryError, BadDatesError
from ..settings import Settings, LocalSettings, ProjectSettings
from ..utils.once import once


JSON = Any


BATCH_CONCURRENCY = 10  # I feel so


def _get_predefined_date_presets(translator) -> list[Version]:
    _ = translator
    today = date.today()
    ret = [
        Version(name=_('batch.date_preset.week'),
                begin=(today - timedelta(weeks=1)).isoformat(),
                end=date.today().isoformat()),
        Version(name=_('batch.date_preset.month'),
                begin=(today - timedelta(days=30)).isoformat(),
                end=date.today().isoformat()),
        Version(name=_('batch.date_preset.half_year'),
                begin=(today - timedelta(days=180)).isoformat(),
                end=date.today().isoformat())  # TODO think better
    ]
    return ret


@once()
def _get_date_presets(settings: Settings) -> list[JSON]:
    ret = list()
    for i in settings.app_config.date_presets:
        ret.append({
            'name': i.name,
            'begin': i.begin,
            'end': i.end
        })
    for i in settings.yt_config.versions:
        ret.append({
            'name': i.name,
            'begin': i.begin.to_datetime().date().isoformat(),
            'end': i.end.to_datetime().date().isoformat()
        })
    return sorted(ret, key=lambda x: x['name'])


@once()
def _get_projects_info(settings: Settings) -> list[JSON]:
    return [proj.to_dict() for proj in settings.yt_config.projects.values()]


def get_basic_batch_context(translator, settings: Settings, sub_mode: str):
    return {
        'projects': _get_projects_info(settings=settings),
        'date_presets': _get_date_presets(settings=settings),
        'predefined_date_presets': _get_predefined_date_presets(translator=translator),
        'batch_sub_mode': sub_mode
    }


def validate_input_params(yt_config: YouTrackInstanceConfig, project: str, components: list[str]):
    if project not in yt_config.projects.keys():
        raise BadQueryError(query_params=['project'])

    unknown_components = set(components) - set(yt_config.projects[project].components)
    if len(unknown_components):
        raise BadQueryError(query_params=list(unknown_components))


def validate_dates(begin: str, end: str) -> tuple[date, date]:
    try:
        begin_date = date.fromisoformat(begin)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise BadDatesError(begin=begin, end=end)

    if end_date < begin_date:
        raise BadDatesError(begin=begin, end=end)
    return begin_date, end_date


def get_required_issue_fields() -> list[str]:
    return [
        'summary',
        'created',
        'resolved',
        'idReadable',
        'numberInProject',
        'customFields(id,name,value(minutes,fullName,name))',
        'project(id,shortName)',
        'tags(name,color(background,foreground))'
    ]


@dataclass
class BatchShortIssueInfo:
    scope: Duration|None = None
    spent_time: Duration|None = None
    priority: str|None = None
    state: str|None = None
    component: str|None = None
    assignee: str|None = None
    project_short_name: str|None = None
    anomalies: list[Anomaly] = field(default_factory=list)

    def has_timings(self) -> bool:
        return self.scope and self.spent_time

    def is_scope_overrun(self) -> bool:
        return self.has_timings() and self.spent_time > self.scope

    def lost_scope(self) -> bool:
        return not self.scope and self.spent_time

    @property
    def overrun(self) -> Duration|None:
        if self.has_timings():
            return self.spent_time - self.scope
        return None


TransformerFunc = Callable[[BatchShortIssueInfo, JSON], JSON]
FilterFunc = Callable[[BatchShortIssueInfo], bool]


def process_issue_custom_fields(json, app_config: LocalSettings,
                                output_transformer_func: TransformerFunc,
                                filter_func: FilterFunc|None = None) -> list[JSON]:
    ret = []
    for entry in json:
        data = BatchShortIssueInfo()
        data.project_short_name = entry['project']['shortName']
        for entry_field in entry['customFields']:
            name, value = entry_field['name'], entry_field['value']

            if not data.assignee and name == 'Assignee':
                data.assignee = value['fullName']
            elif not data.component and name == 'Component':
                data.component = value['name']
            elif not data.state and name == 'State':
                data.state = value['name']
            elif not data.priority and name == 'Priority':
                data.priority = value['name']
            elif not data.scope and name == 'Scope':
                if value:
                    data.scope = Duration.from_minutes(int(value['minutes']))
                else:
                    project_info: ProjectSettings = app_config.projects.get(data.project_short_name, None)
                    data.scope = project_info.default_values.scope if project_info else None
            elif not data.spent_time and name == 'Spent time':
                data.spent_time = Duration.from_minutes(int(value['minutes']))

        if filter_func and not filter_func(data):
            continue
        ret.append(output_transformer_func(data, entry))
    return ret


def batch_output_transformer(parsed: BatchShortIssueInfo, raw: JSON) -> JSON:
    return {
        'id': raw['idReadable'],
        'id_value': int(raw['numberInProject']),
        'project_short_name': parsed.project_short_name,
        'title': raw['summary'],
        'component': parsed.component,
        'created_datetime': raw['created'],
        'resolved_datetime': raw['resolved'],
        'scope': parsed.scope.format_yt() if parsed.scope else None,
        'scope_value': parsed.scope.to_seconds() if parsed.scope else 0,
        'spent_time': parsed.spent_time.format_yt() if parsed.spent_time else None,
        'spent_time_value': parsed.spent_time.to_seconds() if parsed.spent_time else 0,
        'priority': parsed.priority,
        'state': parsed.state,
        'assignee': parsed.assignee,
        'tags': [{'text': i['name'],
                  'bg_color': i['color']['background'],
                  'fg_color': i['color']['foreground']} for i in raw['tags']]
    }


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]
