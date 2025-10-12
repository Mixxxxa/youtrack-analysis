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


from enum import StrEnum


class IssueState:
    class Pre(StrEnum):
        Buffer = 'Buffer'
        OnHold = 'On hold'
        InProgress = 'In progress'
        Review = 'Review'
        Resolved = 'Resolved'
        Suspend = 'Suspend'
        WontFix = 'Wontfix'
        Duplicate = 'Duplicate'


    def __init__(self, value: Pre|str):
        # Значения бывают кастомные, поэтому разрешаем всё кроме пустых
        assert len(value) > 0
        self.__value: IssueState.Pre | str = value

    
    def __eq__(self, other):
        if isinstance(other, IssueState):
            return self.__value == other.__value
        if isinstance(other, IssueState.Pre):
            return self.__value == other
        return NotImplemented
    

    def __str__(self):
        return str(self.__value)


    @staticmethod
    def parse(state: str) -> 'IssueState':
        if len(state) == 0:
            raise RuntimeError('Tried to parse empty state')
        return IssueState(state)


    def is_buffer(self) -> bool:
        return self.__value == IssueState.Pre.Buffer


    def is_hold(self) -> bool:
        return self.__value == IssueState.Pre.OnHold


    def is_in_progress(self) -> bool:
        return self.__value == IssueState.Pre.InProgress


    def is_review(self) -> bool:
        return self.__value == IssueState.Pre.Review


    def is_in_work(self) -> bool:
        P = IssueState.Pre
        return self.__value == P.InProgress or self.__value == P.Review
    

    def is_active(self) -> bool:
        P = IssueState.Pre
        return (
            self.__value == P.Buffer or 
            self.__value == P.OnHold or 
            self.__value == P.InProgress or 
            self.__value == P.Review
        )
    