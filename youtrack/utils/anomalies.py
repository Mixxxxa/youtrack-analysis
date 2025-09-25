from dataclasses import dataclass
from .timestamp import Timestamp
from .duration import Duration
#from flask_babel import _


@dataclass
class Anomaly:
    timestamp: Timestamp


@dataclass
class OverdueAnomaly(Anomaly):
    assignee: str
    def __str__(self):
        return f'Нарушение сроков (overdue): {self.assignee}'


@dataclass
class TooLongReviewAnomaly(Anomaly):
    assignee: str
    expected_time: Duration
    actual_time: Duration

    def __str__(self):
        return f'Нарушение сроков ревью: {self.assignee} ({self.actual_time} вместо {self.expected_time})'


@dataclass
class ShatteredTooLongReviewAnomaly(TooLongReviewAnomaly):
    assignee: str
    def __str__(self):
        return f'Нарушение сроков ревью (c on hold): {self.assignee} ({self.actual_time} вместо {self.expected_time})'


@dataclass
class ScopeOverrunAnomaly(Anomaly):
    assignee: str
    scope: Duration
    spent_time: Duration

    def __str__(self):
        return f'Нарушение Scope задачи: {self.assignee} ({self.spent_time} вместо {self.scope})'
    

@dataclass
class ScopeIncreasedAnomaly(Anomaly):
    before: Duration
    after: Duration

    def __str__(self):
        return f'Скоуп задачи был увеличен: {self.before}->{self.after}'
    
#Ideas:
# Time added manually