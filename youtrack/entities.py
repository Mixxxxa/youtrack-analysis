from datetime import timedelta
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from .utils import Timestamp, Duration, count_working_minutes, is_empty
from .utils.problems import ProblemHolder


UNASSIGNED_NAME = 'Unassigned'


class IssueState(StrEnum):
    Buffer = 'Buffer'
    OnHold = 'On hold'
    InProgress = 'In progress'
    Review = 'Review'
    Resolved = 'Resolved'


@dataclass
class Project:
    short_name: str
    name: str


@dataclass
class CustomField:
    id: str
    name: str

    def __eq__(self, other):
        """Compare without ID
        
        TODO Подумать, нужен ли вообще ID
        """
        if isinstance(other, CustomField):
            return self.name == other.name
        return NotImplemented


@dataclass
class Tag:
    name: str
    background_color: str
    foreground_color: str


@dataclass
class Event:
    timestamp: Timestamp

    def __lt__(self, other):
        if isinstance(other, Event):
            return self.timestamp < other.timestamp
        if isinstance(other, Timestamp):
            return self.timestamp < other
        return NotImplemented
    

@dataclass
class Comment(Event):
    author: str
    text: str


@dataclass
class ValueChangeEvent(Event):
    value: str


@dataclass
class WorkItem(Event):
    name: str
    duration: Duration
    state: str

    def begin(self) -> Timestamp:
        """Возвращает Timestamp начала работы
        """
        return self.timestamp

    def end(self) -> Timestamp:
        """Возвращает Timestamp окончания работы
        """
        return self.timestamp + self.duration
        
    def __str__(self):
        return f"{self.name} - {self.state} - {self.duration.format_yt()}"
    
    @cached_property
    def business_duration(self) -> Duration:
        """Возвращает сколько из общего Duration пришлось на рабочее время
        """
        minutes = count_working_minutes(begin=self.begin().to_datetime(),
                                        end=self.end().to_datetime())
        return Duration.from_minutes(minutes)


@dataclass
class ShortIssueInfo:
    id: str
    summary: str
    author: str
    creation_datetime: Timestamp
    scope: Duration | None
    spent_time_yt: Duration
    current_assignee: str
    state: str
    component: str
    tags: list[Tag]
    subtasks: list['ShortIssueInfo']
    comments: list[Comment]
    project: Project


@dataclass
class IssueInfo(ShortIssueInfo):
    resolve_datetime: Timestamp | None
    started_datetime: Timestamp | None
    work_items: list[WorkItem]
    assignees: list[ValueChangeEvent]
    pauses: list[WorkItem]
    yt_errors: ProblemHolder
    overdues: list[ValueChangeEvent]

    @property
    def resolution_time(self) -> Duration | None:
        """Время решения задачи (от создания до закрытия)"""
        #assert self.resolve_datetime is not None and self.creation_datetime is not None
        if not self.is_finished or self.creation_datetime is None:
            return None
        return self.resolve_datetime - self.creation_datetime
    
    @property
    def reaction_time(self) -> Duration | None:
        """Время реакции на задачу (от создания до взятия в работу)"""
        if self.started_datetime is None or self.creation_datetime is None:
            return None
        return self.started_datetime - self.creation_datetime
    
    @property
    def spent_time_real(self) -> Duration:
        """Время работы по work item'ам в текущей задаче"""
        total = Duration()
        for i in self.work_items:
            total = total + i.duration
        return total

    @property
    def spent_time(self) -> Duration:
        """Общее время работы (Spend Time)"""
        # За основу берём реальный spent_time в задаче
        total = self.spent_time_real        
        # И добавляем к нему значения из подзадач
        for i in self.subtasks:
            total = total + i.spent_time_yt
        return total
    
    @property
    def scope_overrun(self) -> str | None:
        if self.scope is None:
            return None

        spent_time = self.spent_time.to_timedelta()
        scope = self.scope.to_timedelta()
        overrun = scope.total_seconds() - spent_time.total_seconds()
        if overrun >= 0:
            return 'Нет'
                
        as_percent = float(abs(overrun)) / scope.total_seconds() * 100
        return f"{Duration(timedelta(seconds=abs(overrun))).format_yt()} (+{as_percent:.0f}%)"
    
    @property
    def is_started(self) -> bool:
        return self.reaction_time is not None

    @property
    def is_finished(self) -> bool:
        return self.resolve_datetime is not None
    
    def get_activities_range(self) -> tuple[Timestamp, Timestamp|None]:
        """Возвращает диапазон дат между началом первой и концом последней активности"""
        min = self.creation_datetime
        max = self.resolve_datetime

        # workitem'ы отсортированы по возврастанию, поэтому можем проверить только первый
        if not is_empty(self.work_items):
            first_timestamp = self.work_items[0].begin()
            if first_timestamp < min:
                min = first_timestamp

        # Кто-нибудь может создать workitem с не самым последним timestamp, 
        # но более длительным временем работы
        # TODO подумать над оптимизацией
        for i in self.work_items:
            end = i.end()
            if max is None:
                max = end
            elif end > max:
                max = end

        return min,max


def get_issue_spent_time(item: ShortIssueInfo) -> Duration:
    assert isinstance(item, ShortIssueInfo)
    return item.spent_time_yt


def get_workitem_duration(item: WorkItem) -> Duration:
    assert isinstance(item, WorkItem)
    return item.duration


def get_workitem_business_duration(item: WorkItem) -> Duration:
    assert isinstance(item, WorkItem)
    return item.business_duration


def get_event_timestamp(event: Event) -> Timestamp:
    assert isinstance(event, Event)
    return event.timestamp