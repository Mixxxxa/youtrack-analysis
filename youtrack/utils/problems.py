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


from dataclasses import dataclass, field
from enum import Enum, auto


class ProblemKind(Enum):
    DuplicateStateSwitch = auto()   # дублирующийся переход state
    NullScope = auto()              # null вместо scope, хотя в задаче он есть
    SpentTimeInconsistency = auto() # вычесленный SpentTime != значению в YT
    NullBeginScope = auto()         # при изменении Scope значение до None


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
        elif self.kind == ProblemKind.NullBeginScope:
            return []
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
    