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


import re
from urllib.parse import urlparse,parse_qs


# def format_plural(amount: int, variants: list[str]) -> str:
#     assert len(variants) == 3
#     amount = abs(amount)

#     variant: int = 2
#     if amount % 10 == 1 and amount % 100 != 11:
#         variant = 0
#     elif 2 <= amount % 10 <= 4 and (amount % 100 < 10 or amount % 100 >= 20):
#         variant = 1

#     return f'{amount} {variants[variant]}'


def is_empty(container) -> bool:
    return len(container) == 0


def str_to_bool(text: str|int) -> bool:
    return isinstance(text, (str,int)) and str(text).strip().lower() in ['true', '1']


def is_valid_issue_id(id: str) -> bool:
    issue_re = re.compile(r'^[a-z]+?-[0-9]+?$')
    return issue_re.match(id)
    

def extract_issue_id_from_url(url: str, host: str) -> str | None:
    try:
        parts = urlparse(url)
        if parts.scheme != 'https':
            return None
        if parts.hostname is None or parts.hostname != host:
            return None
        if parts.path is None or is_empty(parts.path):
            return None
        
        if parts.path.startswith('/youtrack/agiles/') and not is_empty(parts.query):
            query_parts = parse_qs(qs=parts.query)
            if 'issue' in query_parts and is_valid_issue_id(query_parts['issue'][0]):
                return query_parts['issue'][0]
            
        if parts.path.startswith('/youtrack/issue/'):
            path_parts = [s for s in str.split(parts.path, sep='/') if not is_empty(s.strip())]
            if len(path_parts) > 2 and is_valid_issue_id(path_parts[2]):
                return path_parts[2]
            
        if parts.path.startswith('/issue/'):
            path_parts = [s for s in str.split(parts.path, sep='/') if not is_empty(s.strip())]
            if len(path_parts) > 1 and is_valid_issue_id(path_parts[1]):
                return path_parts[1]
    except:
        pass
    return None


def issue_id_comparator(l: str, r: str) -> int:
    l_parts, r_parts = l.lower().split('-'), r.lower().split('-')
    assert len(l_parts) == 2 and len(r_parts) == 2 and l_parts[0].isascii() and r_parts[0].isascii()
    
    if l_parts[0] < r_parts[0]:
        return -1
    elif l_parts[0] > r_parts[0]:
        return 1
    else:
        l_num, r_num = int(l_parts[1]), int(r_parts[1])
        if l_num < r_num:
            return -1
        elif l_num > r_num:
            return 1
        else:
            return 0
        

def issue_id_to_key(id: str) -> tuple[str, int]:
    parts = id.lower().split('-')
    assert len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit()
    return (parts[0], int(parts[1]))


def is_valid_iso8601_date(value: str) -> bool:
    pattern = r'\d{4}-[01]\d-[0-3]\d' # check only format
    return re.fullmatch(pattern, value) is not None