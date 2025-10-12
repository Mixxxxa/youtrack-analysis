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


from youtrack.helper import YouTrackHelper
import pytest


@pytest.fixture
def helper_auth_data():
    return dict(instance_url='my-yt.myjetbrains.com', api_key='Bearer perm:xxxxxxxxxxxxxxxxxxxxxxxx')


@pytest.mark.parametrize(
    'expected, req', [('id-12680', 'https://my-yt.myjetbrains.com/issue/id-12680'), # Short, but valid URL
                      ('id-12680', 'https://my-yt.myjetbrains.com/youtrack/issue/id-12680'), # Short URL
                      ('id-12680', 'https://my-yt.myjetbrains.com/youtrack/issue/id-12680/Great-big-issue'), # Long URL
                      ('id-12680', 'https://my-yt.myjetbrains.com/youtrack/agiles/120-80/current?issue=id-12680'), # From Agile board
                      ('id-12680', 'https://my-yt.myjetbrains.com/youtrack/agiles/120-80/current?issue=id-12680&wft=true'), # From Agile board, but with garbage
                      ('cpp-1010', 'cpp-1010'), # Only id
                      (None, 'https://my-yt2.myjetbrains.com/youtrack/issue/id-12680'), # Another host
                      (None, 'http://my-yt.myjetbrains.com/youtrack/issue/id-12680'), # Only https. But why?
                      (None, 'https://my-yt.myjetbrains.com/youtrack/agiles/120-80/current'), # Just agile board without issue id
                      ] 
)
def test_parse_issue_id_from_request(helper_auth_data: dict[str,str], req: str, expected: str | None):
    a = YouTrackHelper(**helper_auth_data)
    assert a.extract_issue_id(req) == expected