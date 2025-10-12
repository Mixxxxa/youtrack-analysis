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
from datetime import date


@dataclass
class SearchQueryBuilder:
    project: str|None = None
    components: list[str] = field(default_factory=list)
    resolve_date_begin: date|None = None
    resolve_date_end: date|None = None
    only_started: bool = False
    only_resolved: bool = False
    sort_by: str|None = None
    
    def Build(self) -> str:
        ret = ''

        def append(text: str):
            nonlocal ret
            if len(ret):
                ret += ' '
            ret += text.strip()

        if self.project:
            append(f'project: {self.project}')
        if len(self.components):
            append('Component:')
            append(','.join([self.__escape_component_name(i) for i in self.components]))
        if self.__resolve_date_present():
            append(f'resolved date: {self.resolve_date_begin.isoformat()} .. {self.resolve_date_end.isoformat()}')
        if self.only_resolved:
            append(f'#Resolved')
        if self.only_started:
            append('Spent time: 1m .. *')
        append(f'sort by: {self.sort_by if self.sort_by else "updated"}')
        return ret
    
    @staticmethod
    def __escape_component_name(component: str) -> str:
        if component.find(' ') != -1:
            return f'{{{component}}}'
        return component
    
    def __resolve_date_present(self) -> bool:
        return self.resolve_date_begin and self.resolve_date_end