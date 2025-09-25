from dataclasses import dataclass
from .timestamp import Timestamp
from .issue_state import IssueState


@dataclass(frozen=True)
class ParserContext:
    timestamp: Timestamp
    assignee: str
    state: IssueState