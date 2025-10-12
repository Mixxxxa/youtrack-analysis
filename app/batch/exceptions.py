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


class BadQueryError(ValueError):
    def __init__(self, query_params: list[str]):
        super().__init__()
        self.bad_params = query_params


class BadDatesError(ValueError):
    def __init__(self, begin: str, end: str):
        super().__init__()
        self.begin = begin
        self.end = end


class IncorrectDateFormat(ValueError):
    pass