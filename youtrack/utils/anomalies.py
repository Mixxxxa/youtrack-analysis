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


from dataclasses import dataclass
from .timestamp import Timestamp
from .duration import Duration
from youtrack.utils.parser_context import ParserContext
from youtrack.entities import IssueInfo, WorkItem, IssueState
import logging
from abc import ABC, abstractmethod


anomaly_logger = logging.getLogger("youtrack-anomalies")


@dataclass
class Anomaly(ABC):
    timestamp: Timestamp
    responsible: str 

    @abstractmethod
    def to_string(self, _) -> str:
        pass


@dataclass
class OverdueAnomaly(Anomaly):
    def to_string(self, _) -> str:
        return _('anomaly.overdue')


@dataclass
class TooLongReviewAnomaly(Anomaly):
    fragmented: bool
    expected_time: Duration
    actual_time: Duration

    def to_string(self, _) -> str:
        if self.fragmented:
            return _('anomaly.fragmented_too_long_review') % dict(
                actual_time=self.actual_time.format_yt(),
                expected_time=self.expected_time.format_yt())
        return _('anomaly.too_long_review') % dict( 
                 actual_time=self.actual_time.format_yt(),
                 expected_time=self.expected_time.format_yt())


@dataclass
class ScopeOverrunAnomaly(Anomaly):
    scope: Duration
    spent_time: Duration

    def to_string(self, _) -> str:
        return _('anomaly.scope_overrun') % dict( 
                 scope=self.scope.format_yt(), 
                 spent_time=self.spent_time.format_yt())
    

@dataclass
class ScopeIncreasedAnomaly(Anomaly):
    before: Duration
    after: Duration

    def to_string(self, _) -> str:
        return _('anomaly.scope_increased') % dict(
                 before=self.before.format_yt(), 
                 after=self.after.format_yt(),
                 author=self.responsible)
    

@dataclass
class ReopenAnomaly(Anomaly):
    def to_string(self, _) -> str:
        return _('anomaly.reopen')
    

class AnomaliesDetector:

    def __init__(self, review_thresshold: Duration):
        self.__data: list[Anomaly] = list()

        # Review anomaly
        self.__review_thresshold: Duration = review_thresshold
        self.__review_current_user: str|None = None
        self.__review_current_user_duration = Duration()
        self.__review_current_user_duration_with_hold = Duration()

    
    def get(self) -> list[Anomaly]:
        return self.__data
        
    
    def on_pause_added(self, item: WorkItem) -> None:
        anomaly_logger.debug(f"[Anomaly Detector] OnPause")
        if item.name == self.__review_current_user:
            anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: OnPause ADD {item.business_duration.format_yt()}")
            self.__review_current_user_duration_with_hold += item.business_duration


    def on_tag_added(self, ctx: ParserContext, tag: str) -> None:
        if tag == 'Overdue':
            self.__data.append(OverdueAnomaly(timestamp=ctx.timestamp, 
                                              responsible=ctx.assignee))
            

    def on_work_added(self, ctx: ParserContext, item: WorkItem) -> None:
        """_summary_
        1. Получили задачу на ревью и оно шло больше двух рабочих дней
        2. Получили задачу на ревью, перенесли в hold и это (вместе с ревью) заняло больше двух рабочих дней
        3. Получили задачу на ревью, и во время этого "не assignee" вручную добавил время в счетчик 
        Проверяем при смене state (если ревью, то начинаем поиск) или assignee (заканчиваем поиск и начинаем заного если все ещё ревью)

        Мы не можем смотреть это "в конце", т.к. смена assignee не всегда происходит вместе со сменой state (нужно завозить нормализацию данных)
        Args:
            item (WorkItem): _description_
        """
        # защита от сторонних ревьюверов
        from_current_assignee = item.name == ctx.assignee
        if item.state.is_review() and from_current_assignee:
            if self.__review_current_user is None:
                # начинаем поиск слишком долгих ревью
                anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: Begin for '{item.name}'")
                self.__review_current_user = item.name

            anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: WorkItem ADD {item.business_duration.format_yt()}")
            self.__review_current_user_duration += item.business_duration
            self.__review_current_user_duration_with_hold += item.duration


    def on_assignee_changed(self, ctx: ParserContext, assignee: str) -> None:
        anomaly_logger.debug(f"[Anomaly Detector] OnAssigneeChanged")
        if self.__review_current_user is not None and self.__review_current_user != assignee:
            self.__check_too_long_review_anomaly(current_timestamp=ctx.timestamp)

    
    def on_scope_changed(self, ctx: ParserContext, before: Duration, after: Duration, author: str) -> None: #++
        if before < after:
            self.__data.append(ScopeIncreasedAnomaly(timestamp=ctx.timestamp, 
                                                     responsible=author,
                                                     before=before, 
                                                     after=after))


    def on_state_changed(self, ctx: ParserContext, state: IssueState) -> None:
        anomaly_logger.debug(f"[Anomaly Detector] OnStateChanged")
        if self.__review_current_user is not None:
            if not state.is_hold() and not state.is_review():
                self.__check_too_long_review_anomaly(current_timestamp=ctx.timestamp)


    def on_parsing_finished(self, issue: IssueInfo) -> None:
        anomaly_logger.debug(f"[Anomaly Detector] OnParsingFinished")
        latest_timestamp = issue.resolve_datetime or Timestamp.now()

        if issue.scope and issue.spent_time_yt and issue.spent_time_yt > issue.scope:
            # TODO Нужно считать прямо по ходу дела (могли менять скоуп и снова его пробивать)
            # Проблема в том, что сейчас Spent Time высчитывается только в самом конце (из-за подзадач)
            self.__data.append(ScopeOverrunAnomaly(timestamp=latest_timestamp, 
                                                   responsible='', 
                                                   scope=issue.scope, 
                                                   spent_time=issue.spent_time_yt))
        if self.__review_current_user is not None:
            self.__check_too_long_review_anomaly(latest_timestamp)


    def __check_too_long_review_anomaly(self, current_timestamp: Timestamp):
        anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: Check")
        is_too_long = self.__review_current_user_duration > self.__review_thresshold
        is_too_long_with_hold = self.__review_current_user_duration_with_hold > self.__review_thresshold
        with_hold_is_longer = self.__review_current_user_duration_with_hold > self.__review_current_user_duration

        if is_too_long or is_too_long_with_hold:
            anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: Found")
            self.__data.append(TooLongReviewAnomaly(timestamp=current_timestamp,
                                                    responsible=self.__review_current_user,
                                                    fragmented=with_hold_is_longer,
                                                    expected_time=self.__review_thresshold,
                                                    actual_time=self.__review_current_user_duration_with_hold if with_hold_is_longer else self.__review_current_user_duration))
        anomaly_logger.debug(f"[Anomaly Detector] TooLongReview: Reset")
        self.__review_current_user = None
        self.__review_current_user_duration = Duration()
        self.__review_current_user_duration_with_hold = Duration()


    