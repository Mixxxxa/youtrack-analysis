from datetime import timedelta
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from .utils import Timestamp, Duration, count_working_minutes


UNASSIGNED_NAME = 'Unassigned'


class IssueState(StrEnum):
    Buffer = 'Buffer'
    OnHold = 'On hold'
    InProgress = 'In progress'
    Review = 'Review'
    Resolved = 'Resolved'


@dataclass
class CustomField:
    id: str
    name: str


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
        return self.timestamp

    def end(self) -> Timestamp:
        return self.timestamp + self.duration
        
    def __str__(self):
        return f"{self.name} - {self.state} - {self.duration.format_yt()}"
    
    @cached_property
    def business_duration(self) -> Duration:
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
    tags: list[Tag]
    subtasks: list['ShortIssueInfo']
    comments: list[Comment]


@dataclass
class IssueInfo(ShortIssueInfo):
    resolve_datetime: Timestamp | None
    started_datetime: Timestamp | None
    work_items: list[WorkItem]
    assignees: list[ValueChangeEvent]
    pauses: list[WorkItem]
    yt_errors: list[str]
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
    def spent_time(self) -> Duration:
        """Общее время работы (Spend Time)"""
        # built-in sum doesn't work here because holds intermediate values as int
        total = Duration()
        for i in self.work_items:
            total = total + i.duration
        
        # YT автоматически вливает время подзадач в Spent Time основной задачи
        # Чтобы сходилось время нужно это учитывать
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
        return f"{Duration(timedelta(seconds=abs(overrun))).format_business()} (+{as_percent:.0f}%)"
    
    @property
    def is_started(self) -> bool:
        return self.reaction_time is not None

    @property
    def is_finished(self) -> bool:
        return self.resolve_datetime is not None
    
    def to_dict(self):
        overdues = [{'date': i.timestamp.format_ru(), 
                     'name': i.value} for i in self.overdues]
        tags = [{'text': i.name, 
                 'bg_color': i.background_color, 
                 'fg_color': i.foreground_color} for i in self.tags]
        comments = [{'creation_datetime': i.timestamp.format_ru(),
                     'author': i.author, 
                     'text': i.text} for i in self.comments]
        
        pauses_total = Duration()
        pauses_total_business = Duration()
        pauses_sorted = sorted(self.pauses, key=lambda x: x.business_duration, reverse=True)
        for i in pauses_sorted:
            pauses_total += i.duration
            pauses_total_business += i.business_duration
        pauses = [{'name': i.name,
                   'begin': i.begin().format_ru(),
                   'end': i.end().format_ru(),
                   'duration': i.duration.format_natural(),
                   'duration_business': i.business_duration.format_business(),
                   'percents': f'{i.business_duration.to_seconds() / pauses_total_business.to_seconds() * 100:.2f}'} for i in pauses_sorted]

        subtasks = []
        subtasks_total_spent_time = Duration()
        for i in sorted(self.subtasks, key=lambda x: x.spent_time_yt, reverse=True):
            subtasks_total_spent_time += i.spent_time_yt
            subtasks.append({'id': i.id,
                             'title': i.summary,
                             'state': i.state,
                             'spent_time': i.spent_time_yt.format_business(),
                             'percent': f'{i.spent_time_yt.to_seconds() / self.spent_time_yt.to_seconds() * 100:.2f}'})

        return {
            # Basic
            'id': self.id,
            'summary': self.summary,
            'author': self.author,
            'state': self.state,
            'is_resolved': self.is_finished,
            'scope': self.scope.format_business() if self.scope else None,
            'scope_overrun': self.scope_overrun,
            'creation_datetime': self.creation_datetime.format_ru(),
            'spent_time': self.spent_time.format_business(),
            'reaction_time': self.reaction_time.format_natural() if self.is_started else None,
            'resolution_time': self.resolution_time.format_natural() if self.is_finished else None,

            # Containers
            'overdues': overdues,
            'tags': tags,
            'comments': comments,
            'yt_errors': self.yt_errors,
            'pauses': {
                'total': pauses_total.format_natural(),
                'total_business': pauses_total_business.format_business(),
                'entries': pauses
            },
            'subtasks': {
                'total': subtasks_total_spent_time.format_business(),
                'entries': subtasks
            }
        }
        pass