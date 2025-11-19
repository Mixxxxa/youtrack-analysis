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


import pytest
from youtrack.utils.issue_state import IssueState


@pytest.mark.parametrize(
    'text, expected', [
        ('Buffer', IssueState.Pre.Buffer),
        ('On hold', IssueState.Pre.OnHold),
        ('In progress', IssueState.Pre.InProgress),
        ('Review', IssueState.Pre.Review),
        ('Resolved', IssueState.Pre.Resolved),
        ('Suspend', IssueState.Pre.Suspend),
        ('Wontfix', IssueState.Pre.WontFix),
        ('Duplicate', IssueState.Pre.Duplicate)
    ]
)
def test_parse(text: str, expected: IssueState.Pre):
    v = IssueState.parse(text)
    assert v == expected
    assert str(v) == text


@pytest.mark.parametrize(
    'value, buffer, on_hold, in_progress, review, in_work, active', [
                                  # Buf  | Hold | InProgress | Review  | In work | Active
        (IssueState.Pre.Buffer,      True, False,       False,    False,    False,  True),
        (IssueState.Pre.OnHold,     False,  True,       False,    False,    False,  True),
        (IssueState.Pre.InProgress, False, False,        True,    False,     True,  True),
        (IssueState.Pre.Review,     False, False,       False,     True,     True,  True),
        (IssueState.Pre.Resolved,   False, False,       False,    False,    False, False),
        (IssueState.Pre.Suspend,    False, False,       False,    False,    False, False),
        (IssueState.Pre.WontFix,    False, False,       False,    False,    False, False),
        (IssueState.Pre.Duplicate,  False, False,       False,    False,    False, False)
    ]
)
def test_special_functions(value: IssueState.Pre, buffer: bool, on_hold: bool,
                           in_progress: bool, review: bool, in_work: bool, active: bool):
    v = IssueState(value)
    assert v.is_buffer() == buffer
    assert v.is_hold() == on_hold
    assert v.is_in_progress() == in_progress
    assert v.is_review() == review
    assert v.is_in_work() == in_work
    assert v.is_active() == active


@pytest.mark.parametrize(
    'value, buffer, on_hold, in_progress, review, in_work, active', [
                        # Buf  | Hold | InProgress | Review  | In work | Active
        ('Todo',          False, False,       False,    False,    False, False),
        ('Issue Created', False, False,       False,    False,    False, False),
    ]
)
def test_handle_custom_states(value: str, buffer: bool, on_hold: bool,
                              in_progress: bool, review: bool, in_work: bool, active: bool):
    a = IssueState.parse(value)
    assert a.is_buffer() == buffer
    assert a.is_hold() == on_hold
    assert a.is_in_progress() == in_progress
    assert a.is_review() == review
    assert a.is_in_work() == in_work
    assert a.is_active() == active
    assert str(a) == value


def test_incorrect_parse():
    with pytest.raises(RuntimeError) as excinfo:
        IssueState.parse('')
    assert excinfo.type is RuntimeError
    assert "Tried to parse empty state" in str(excinfo.value)


def test_compare():
    P = IssueState.Pre
    assert IssueState(P.Buffer) == IssueState(P.Buffer)
    assert IssueState(P.Buffer) != IssueState(P.OnHold)
