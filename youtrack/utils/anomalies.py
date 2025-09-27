from dataclasses import dataclass
from .timestamp import Timestamp
from .duration import Duration
from flask_babel import _


@dataclass
class Anomaly:
    timestamp: Timestamp
    responsible: str 


@dataclass
class OverdueAnomaly(Anomaly): #+
    def __str__(self):
        return _('anomaly.overdue')


@dataclass
class TooLongReviewAnomaly(Anomaly):
    fragmented: bool
    expected_time: Duration
    actual_time: Duration

    def __str__(self):
        if self.fragmented:
            return _('anomaly.fragmented_too_long_review',
                 actual_time=self.actual_time,
                 expected_time=self.expected_time)
        return _('anomaly.too_long_review', 
                 actual_time=self.actual_time,
                 expected_time=self.expected_time)


@dataclass
class ScopeOverrunAnomaly(Anomaly):
    scope: Duration
    spent_time: Duration

    def __str__(self):
        return _('anomaly.scope_overrun', 
                 scope=self.scope, 
                 spent_time=self.spent_time)
    

@dataclass
class ScopeIncreasedAnomaly(Anomaly): #+
    before: Duration
    after: Duration

    def __str__(self):
        return _('anomaly.scope_increased', 
                 before=self.before.format_yt(), 
                 after=self.after.format_yt())
    
#Ideas:
# Time added manually