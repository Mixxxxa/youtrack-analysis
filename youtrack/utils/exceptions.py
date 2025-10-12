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


class InvalidIssueIdError(RuntimeError):
    def __init__(self, id: str, *args):
        super().__init__(f"Invalid issue id or url: '{id}'" , *args)


class ParsingError(RuntimeError):
    def __init__(self, id: str, message: str):
        super().__init__(f"Unable to parse data from issue '{id}': {message}")


class TooMuchIssuesInBatchError(RuntimeError):
    def __init__(self, count: int):
        super().__init__()
        self.count = count


class UnableToCountIssues(RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)