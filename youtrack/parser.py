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


from .entities import (
    UNASSIGNED_NAME,
    get_issue_spent_time,
    WorkItem,
    IssueInfo,
    CustomFields,
    Project,
    Tag,
    Comment,
    ValueChangeEvent,
    ShortIssueInfo,
    CustomField
)
from .utils import yt_logger
from .utils.duration import Duration
from .utils.timestamp import Timestamp
from .utils.others import is_empty
from .utils.exceptions import ParsingError
from .utils.problems import ProblemHolder, ProblemKind
from math import fabs
from contextlib import contextmanager
from .utils.issue_state import IssueState
from .utils.parser_context import ParserContext
from .utils.callback_manager import CallbackManager
from typing import Protocol, runtime_checkable


@runtime_checkable
class PauseAddedCallback(Protocol):
    def __call__(item: WorkItem) -> None: ...


@runtime_checkable
class TagAddedCallback(Protocol):
    def __call__(ctx: ParserContext, tag: str) -> None: ...


@runtime_checkable
class WorkAddedCallback(Protocol):
    def __call__(ctx: ParserContext, item: WorkItem) -> None: ...


@runtime_checkable
class AssigneeChangedCallback(Protocol):
    def __call__(ctx: ParserContext, assignee: str) -> None: ...


@runtime_checkable
class ScopeChangedCallback(Protocol):
    def __call__(ctx: ParserContext, before: Duration, after: Duration, author: str) -> None: ...


@runtime_checkable
class StateChangedCallback(Protocol):
    def __call__(ctx: ParserContext, state: IssueState) -> None: ...


@runtime_checkable
class ParsingFinishedCallback(Protocol):
    def __call__(issue: IssueInfo) -> None: ...


class IssueParser:
    def __init__(self, custom_fields: CustomFields):
        # Settings
        self.__custom_fields: CustomFields = custom_fields

        # Callbacks
        self.cb_pause_added = CallbackManager(PauseAddedCallback)
        self.cb_tag_added = CallbackManager(TagAddedCallback)
        self.cb_work_added = CallbackManager(WorkAddedCallback)
        self.cb_assignee_changed = CallbackManager(AssigneeChangedCallback)
        self.cb_scope_changed = CallbackManager(ScopeChangedCallback)
        self.cb_state_changed = CallbackManager(StateChangedCallback)
        self.cb_parsing_finished = CallbackManager(ParsingFinishedCallback)

        # Parser state
        self.__parser_previous_on_hold_begin: Timestamp | None = None
        self.__parser_current_state: IssueState | None = None
        self.__parser_process_links: bool = False

        # Data
        self.__id: str | None = None
        self.__summary: str | None = None
        self.__current_assignee: str | None = None
        self.__author: str | None = None
        self.__state: IssueState | None = None
        self.__component: str | None = None
        self.__scope: Duration | None = None
        self.__project: Project | None = None
        self.__spent_time_yt: Duration | None = None
        self.__creation_datetime: Timestamp | None = None
        self.__resolve_datetime: Timestamp | None = None
        self.__started_datetime: Timestamp | None = None
        self.__tags: list[Tag] = list()
        self.__comments: list[Comment] = list()
        self.__work_items: list[WorkItem] = list()
        self.__pauses: list[WorkItem] = list()
        self.__assignees: list[ValueChangeEvent] = list()
        self.__subtasks: list[ShortIssueInfo] = list()
        self.__yt_errors: ProblemHolder = ProblemHolder()

    def __get_context(self, timestamp: Timestamp) -> ParserContext:
        return ParserContext(timestamp=timestamp,
                             assignee=self.__get_current_assignee(),
                             state=self.__parser_current_state)

    @contextmanager
    def __link_parse_guard(self, new_value: bool|None = None):
        """Guard for automatic restore parser state after processing links

        It should be as separate class or func but the target value is private
        TODO Test it somehow
        """
        original_value = self.__parser_process_links
        try:
            if new_value is not None:
                self.__parser_process_links = new_value
            yield self.__parser_process_links
        finally:
            self.__parser_process_links = original_value

    def __pre_parse_activities(self, json) -> None:
        # Проблемы которые не удалось решить парсингом в один проход:
        # + Кому засчитывать время (паузы) если смен Assignee до этого не было
        # + Какой вид активности засчитывать если смен State до этого не было
        # Чтобы решить эти неоднозначности (без обратных проходов с исправлением уже готовых записей)
        # собираем информацию до основного парсинга
        assert self.__current_assignee is not None
        assert self.__state is not None
        assert self.__creation_datetime is not None, '__creation_datetime is empty'

        for entry in json:
            if entry['$type'] != 'CustomFieldActivityItem':
                continue

            target_member = entry['targetMember']
            if is_empty(self.__assignees) and target_member == '__CUSTOM_FIELD__Assignee_3':
                before: str = UNASSIGNED_NAME if is_empty(entry['removed']) else entry['removed'][0]['name']
                self.__add_assignee(timestamp=self.__creation_datetime, name=before)
            elif self.__parser_current_state is None and target_member == '__CUSTOM_FIELD__State_2':
                before = IssueState.parse(entry['removed'][0]['name'])
                self.__add_state(timestamp=self.__creation_datetime, state=before)

            if not is_empty(self.__assignees) and self.__parser_current_state is not None:
                break

        # HACK: Если смен Assignee не было, то берём текущего
        if is_empty(self.__assignees):
            self.__add_assignee(timestamp=self.__creation_datetime,
                                name=self.__current_assignee)
        # HACK: Если смен State не было, то берём текущую
        if self.__parser_current_state is None:
            self.__add_state(timestamp=self.__creation_datetime,
                             state=self.__state)
        # Если начали сразу с On Hold, то начинаем паузу
        # Может показаться логичнее записывать паузы только после начала работы над задачей (перехода в in progress),
        # но тогда потеряются куча задач, которые сразу создают в on hold и больше они никуда не двигаются
        if self.__parser_current_state.is_hold():
            self.__begin_pause(self.__creation_datetime)
        # Если начали с активного state, то ставим отметку о начале работы
        if self.__parser_current_state.is_in_work():
            self.__add_started(timestamp=self.__creation_datetime)

    def __write_yt_error(self, kind: ProblemKind, msg='') -> None:
        if self.__parser_process_links and kind == ProblemKind.NullScope:
            return
        yt_logger.warning(f"Detected YT API error ({kind}). Details: '{msg}'")
        self.__yt_errors.add(kind, msg)

    def __parse_short_info(self, issue_info) -> ShortIssueInfo:
        """ Parse info
        https://www.jetbrains.com/help/youtrack/devportal/api-entity-Issue.html
        """
        scope: Duration | None = None
        spent_time: Duration | None = None
        tags: list[Tag] = list()
        comments: list[Comment] = list()
        subtasks: list['ShortIssueInfo'] = list()
        current_assignee: str = UNASSIGNED_NAME
        state: IssueState | None = None
        component: str | None = None
        project: Project | None = None

        project = Project(short_name=issue_info['project']['shortName'],
                          name=issue_info['project']['name'],
                          id=issue_info['project']['id'])

        for i in issue_info['customFields']:
            name, value = i['name'], i['value']
            field = CustomField(id=i['id'], name=name)

            if not state and field == self.__custom_fields.state:
                state = IssueState.parse(value['name'])
            elif not current_assignee and field == self.__custom_fields.assignee:
                current_assignee = value['fullName']
            elif not scope and field == self.__custom_fields.scope:
                if value is not None:
                    scope = Duration.from_minutes(int(value['minutes']))
                else:
                    # Scope должен быть, но иногда не отдаётся API
                    self.__write_yt_error(ProblemKind.NullScope, 'API has returned NULL Scope')
            elif not spent_time and field == self.__custom_fields.spent_time and value is not None:
                spent_time = Duration.from_minutes(int(value['minutes']))
            elif not component and field == self.__custom_fields.component:
                component = value['name']

        for i in issue_info['tags']:
            tags.append(Tag(name=i['name'],
                            background_color=i['color']['background'],
                            foreground_color=i['color']['foreground']))

        for i in issue_info['comments']:
            comments.append(Comment(timestamp=Timestamp.from_yt(i['created']),
                                    author=i['author']['fullName'],
                                    text=i['text']))

        # Parse links with guard
        if not self.__parser_process_links and 'links' in issue_info:
            with self.__link_parse_guard(True):
                for entry in issue_info['links']:
                    if entry['direction'] == 'OUTWARD' and entry['linkType']['sourceToTarget'] == 'parent for':
                        for i in entry['issues']:
                            subtasks.append(self.__parse_short_info(i))

        return ShortIssueInfo(
            id=issue_info['idReadable'],
            summary=issue_info['summary'],
            author=issue_info['reporter']['fullName'],
            creation_datetime=Timestamp.from_yt(issue_info['created']),
            scope=scope,
            spent_time_yt=spent_time if spent_time is not None else Duration(),
            tags=tags,
            comments=comments,
            subtasks=subtasks,
            state=state,
            current_assignee=current_assignee,
            component=component,
            project=project
        )

    def parse_custom_fields(self, entry) -> None:
        info = self.__parse_short_info(entry)
        self.__id = info.id
        self.__summary = info.summary
        self.__add_created(timestamp=info.creation_datetime, name=info.author)
        self.__scope = info.scope
        self.__spent_time_yt = info.spent_time_yt
        self.__current_assignee = info.current_assignee
        self.__state = info.state
        self.__tags = info.tags
        self.__comments = info.comments
        self.__subtasks = info.subtasks
        self.__component = info.component
        self.__project = info.project

    def __parse_activity(self, entry) -> None:
        timestamp = Timestamp.from_yt(entry['timestamp'])
        entry_type = entry['$type']

        if entry_type == 'IssueResolvedActivityItem':
            self.__add_resolved(timestamp=timestamp,
                                name=entry['author']['name'])

        elif entry_type == 'TagsActivityItem' and not is_empty(entry['added']):
            ctx = ParserContext(timestamp=timestamp, assignee=self.__get_current_assignee(), state=self.__parser_current_state)
            tag = entry['added'][0]['name']
            self.cb_tag_added(ctx=ctx, tag=tag)

        elif entry_type == 'WorkItemActivityItem':
            duration = Duration.from_minutes(int(entry['added'][0]['duration']['minutes']))
            fixed_timestamp = timestamp

            # Если событие в начале дня, то зачитываем время во вчерашний день
            if timestamp.is_day_start():
                fixed_timestamp = fixed_timestamp.to_end_of_previous_business_day()

            fixed_timestamp = fixed_timestamp - duration
            self.__add_work_item(timestamp=fixed_timestamp,
                                 name=entry['author']['name'],
                                 duration=duration,
                                 state=self.__parser_current_state)

        elif entry_type == 'CustomFieldActivityItem':
            target_member = entry['targetMember']

            if target_member == '__CUSTOM_FIELD__Assignee_3':
                before: str = UNASSIGNED_NAME if is_empty(entry['removed']) else entry['removed'][0]['name']
                after: str = UNASSIGNED_NAME if is_empty(entry['added']) else entry['added'][0]['name']
                self.__switch_assignee(timestamp=timestamp,
                                       before=before,
                                       after=after)

            elif target_member == '__CUSTOM_FIELD__State_2':
                before = IssueState.parse(entry['removed'][0]['name'])
                after = IssueState.parse(entry['added'][0]['name'])
                self.__switch_state(timestamp=timestamp,
                                    before=before,
                                    after=after)

            elif target_member == '__CUSTOM_FIELD__Estimation_19':
                before: str|None = entry['removed']
                after: Duration = Duration.from_minutes(entry['added'] or 0)
                if before is None:
                    self.__write_yt_error(ProblemKind.NullBeginScope,
                                          f"Detected Scope change, but the value before is unknown (Empty->{after.format_yt()})")
                    return

                self.cb_scope_changed(ctx=self.__get_context(timestamp),
                                      before=Duration.from_minutes(entry['removed'] or 0),
                                      after=after,
                                      author=entry['author']['name'])

    def parse_activities(self, json) -> None:
        self.__pre_parse_activities(json)
        for entry in json:
            self.__parse_activity(entry)

    def __finalize(self) -> None:
        if self.__is_in_pause():
            self.__end_pause(timestamp=Timestamp.now())

        total_spent_time = Duration()
        for i in self.__work_items:
            total_spent_time += i.duration
        for i in self.__subtasks:
            total_spent_time += i.spent_time_yt

        # Если посчитанное нами и YT время не сходится, то нужно исследовать причину
        # Иногда случается из-за того что подзадачу слинковали не сразу, а поэтому
        # нужно выявлять этот момент и считать только его
        if self.__spent_time_yt != total_spent_time:
            self.__write_yt_error(ProblemKind.SpentTimeInconsistency,
                                  'The value in YouTrack field \'Spent Time\' is not equal to calculated Spent Time')

        # Логичнее сортировать по ID, но в таком виде оно нигде не используется.
        # Поэтому сортируем по убыванию spent time
        self.__subtasks.sort(key=get_issue_spent_time, reverse=True)

        # Заплатка для широко распространнего способа ограничения перемещения задач
        # (добавление workitem'a длинной в 1 минуту)
        if len(self.__work_items) > 1:
            elem0 = self.__work_items[0]
            buffer_or_onhold = elem0.state.is_buffer() or elem0.state.is_hold()
            if buffer_or_onhold and elem0.duration == Duration.from_minutes(1):
                elem0.state = self.__work_items[1].state
                yt_logger.debug('Fixed 1m buffer')

        # !!! Эта операция всегда должна быть последней !!!
        # !!! Иначе сломаются фиксы выше                !!!
        # Сортируем все workitem'ы по времени создания
        # для стабилизации и ускорения дальнейшей обработки
        self.__work_items.sort()

    def get_result(self) -> IssueInfo:
        self.__finalize()
        ret = IssueInfo(
            id=self.__id,
            summary=self.__summary,
            scope=self.__scope,
            spent_time_yt=self.__spent_time_yt,
            current_assignee=self.__current_assignee,
            state=self.__state,
            tags=self.__tags,
            comments=self.__comments,
            author=self.__author,
            creation_datetime=self.__creation_datetime,
            resolve_datetime=self.__resolve_datetime,
            started_datetime=self.__started_datetime,
            work_items=self.__work_items,
            assignees=self.__assignees,
            pauses=self.__pauses,
            subtasks=self.__subtasks,
            yt_errors=self.__yt_errors,
            component=self.__component,
            project=self.__project,
        )
        self.cb_parsing_finished(issue=ret)
        return ret

    def __add_state(self, timestamp: Timestamp, state: IssueState) -> None:
        assert isinstance(timestamp, Timestamp)
        assert isinstance(state, IssueState)
        if self.__parser_current_state is None:
            yt_logger.debug(f"{timestamp} [State] {state}")
        else:
            yt_logger.debug(f"{timestamp} [State] {self.__parser_current_state} -> {state}")
        self.__parser_current_state = state

    def __switch_state(self, timestamp: Timestamp, before: IssueState, after: IssueState) -> None:
        assert isinstance(timestamp, Timestamp)
        assert isinstance(before, IssueState)
        assert isinstance(after, IssueState)
        if before == after:
            raise RuntimeError(f"Tried to change state to the same: '{before}' -> '{after}'")

        if before != self.__parser_current_state:
            is_duplicate = False
            if len(self.__work_items) > 2:
                # TODO Это не сработает если дубликат в начале задачи
                is_same_before = self.__work_items[-2].state == before
                is_same_after = self.__work_items[-1].state == after
                # Timestamp почему-то разный, поэтому не сравниваем
                is_duplicate = is_same_before and is_same_after

            if is_duplicate:
                self.__write_yt_error(ProblemKind.DuplicateStateSwitch,
                                      f"{timestamp} Duplicate state switch for '{self.__get_current_assignee()}': '{before}'->'{self.__parser_current_state}'")  # noqa: E501
                # Встречал всего один раз и там оказалось не критично, поэтому просто игнорим запись
                return
            else:
                raise RuntimeError(f"{timestamp} Previous state mismatch: '{before}'!='{self.__parser_current_state}'")

        # Паузы в работе
        if before.is_hold():
            self.__end_pause(timestamp=timestamp.prev_second())
        if after.is_hold():
            self.__begin_pause(timestamp)

        # Начало работы над задачей
        if self.__started_datetime is None and after.is_in_work():
            self.__add_started(timestamp=timestamp)

        # Сброс статуса завершенной задачи если её вернули с того света
        if self.__resolve_datetime is not None and after.is_active():
            self.__resolve_datetime = None
        self.__add_state(timestamp=timestamp, state=after)
        self.cb_state_changed(ctx=self.__get_context(timestamp), state=after)

    def __add_started(self, timestamp: Timestamp) -> None:
        assert not is_empty(self.__assignees)
        self.__started_datetime = timestamp
        yt_logger.debug(f"{timestamp} [Started] by {self.__get_current_assignee()}")

    def __add_created(self, timestamp: Timestamp, name: str) -> None:
        assert isinstance(timestamp, Timestamp)
        self.__author = name
        self.__creation_datetime = timestamp
        yt_logger.debug(f"{timestamp} [Created] by {self.__author}")

    def __add_resolved(self, timestamp: Timestamp, name: str) -> None:
        assert isinstance(timestamp, Timestamp)
        self.__resolve_datetime = timestamp
        yt_logger.debug(f"{timestamp} [Resolved] by {name}")

    def __add_work_item(self, timestamp: Timestamp, name: str, duration: Duration, state: IssueState) -> None:
        assert isinstance(timestamp, Timestamp)
        assert isinstance(duration, Duration)
        assert isinstance(state, IssueState)
        temp = WorkItem(name=name,
                        timestamp=timestamp,
                        duration=duration,
                        state=state)
        self.__work_items.append(temp)
        yt_logger.debug(f"{timestamp} [Time] {temp}")
        self.cb_work_added(ctx=self.__get_context(timestamp), item=temp)

    def __is_in_pause(self) -> bool:
        return self.__parser_previous_on_hold_begin is not None

    def __get_current_assignee(self) -> str:
        return self.__assignees[-1].value

    def __begin_pause(self, timestamp: Timestamp) -> None:
        self.__parser_previous_on_hold_begin = timestamp

    def __end_pause(self, timestamp: Timestamp) -> None:
        """Добавление паузы в лог. Паузы меньше одной минуты пропускаются"""
        assert isinstance(timestamp, Timestamp)
        assert self.__parser_previous_on_hold_begin is not None

        delta_with_previous = timestamp - self.__parser_previous_on_hold_begin
        # Если пауза меньше минуты, то пропускаем
        # TODO Сделать проверку на work minutes, т.к. можно хитро закончить паузу утром и получить кучу лишнего холда
        if fabs(delta_with_previous.to_timedelta().total_seconds()) > 60:
            temp = WorkItem(name=self.__get_current_assignee(),
                            timestamp=self.__parser_previous_on_hold_begin,
                            duration=delta_with_previous,
                            state=IssueState(IssueState.Pre.OnHold))
            self.__pauses.append(temp)
            yt_logger.debug(f"{self.__parser_previous_on_hold_begin} [Pause] {temp}")
            self.cb_pause_added(item=temp)
        self.__parser_previous_on_hold_begin = None

    def __add_assignee(self, timestamp: Timestamp, name: str):
        if is_empty(self.__assignees):
            yt_logger.debug(f"{timestamp} [Assignee] {name}")
        else:
            yt_logger.debug(f"{timestamp} [Assignee] {self.__get_current_assignee()} -> {name}")
        self.__assignees.append(ValueChangeEvent(timestamp=timestamp,
                                                 value=name))

    def __switch_assignee(self, timestamp: Timestamp, before: str, after: str):
        if is_empty(before) and is_empty(after):
            raise ParsingError(self.__id, 'No assignee passed')
        if before == after:
            raise ParsingError(self.__id, 'Self assign detected')

        # При смене assignee также нужно добавлять паузу на прошлого assignee
        if self.__is_in_pause():
            self.__end_pause(timestamp=timestamp.prev_second())
            # Начинаем новую сессию паузы
            self.__begin_pause(timestamp=timestamp)

        before_check = self.__get_current_assignee()
        assert before == before_check, f"Previous assignee mismatch. '{before}'!= '{before_check}'"
        self.__add_assignee(timestamp=timestamp, name=after)
