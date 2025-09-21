from dataclasses import dataclass, field
from enum import Enum, auto


class ProblemKind(Enum):
    DuplicateStateSwitch = auto()   # дублирующийся переход state
    NullScope = auto()              # null вместо scope, хотя в задаче он есть
    SpentTimeInconsistency = auto() # вычесленный SpentTime != значению в YT


@dataclass
class IssueProblem:
    """Описание проблемы с YouTrack"""

    class AffectedField(Enum):
        SpentTime = auto()
        ScopeOverrun = auto()
        State = auto()

    kind: ProblemKind
    msg: str = ''

    @property
    def affected_fields(self) -> list['IssueProblem.AffectedField']:
        if self.kind == ProblemKind.DuplicateStateSwitch:
            return [IssueProblem.AffectedField.SpentTime, IssueProblem.AffectedField.State]
        elif self.kind == ProblemKind.NullScope:
            return [IssueProblem.AffectedField.SpentTime, 
                    IssueProblem.AffectedField.ScopeOverrun]
        elif self.kind == ProblemKind.SpentTimeInconsistency:
            return [IssueProblem.AffectedField.SpentTime]
        raise NotImplementedError("Unknown YT problem kind")
    
    @property
    def details(self) -> str:
        if len(self.msg):
            return self.msg
        return ''
    

@dataclass
class ProblemHolder:
    def __init__(self):
        self.__data: list[IssueProblem] = list()

    def get(self) -> list[IssueProblem]:
        return self.__data
    
    def add(self, kind: ProblemKind, msg: str = ''):
        self.__data.append(IssueProblem(kind=kind, msg=msg))
    