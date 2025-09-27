import pytest
from youtrack import IssueState

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
def test_special_functions(value: IssueState.Pre, buffer: bool, on_hold: bool, in_progress: bool, review: bool, in_work: bool, active: bool):
    v = IssueState(value)
    assert v.is_buffer() == buffer
    assert v.is_hold() == on_hold
    assert v.is_in_progress() == in_progress
    assert v.is_review() == review
    assert v.is_in_work() == in_work
    assert v.is_active() == active


def test_incorrect_parse():
    with pytest.raises(RuntimeError) as excinfo:
        IssueState.parse('Something')
    assert excinfo.type is RuntimeError
    assert "Unknown issue state 'something'" in str(excinfo.value)


def test_compare():
    P = IssueState.Pre
    assert IssueState(P.Buffer) == IssueState(P.Buffer)
    assert IssueState(P.Buffer) != IssueState(P.OnHold)
