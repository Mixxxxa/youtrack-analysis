from youtrack import is_empty, str_to_bool, issue_id_comparator, issue_id_to_key
from functools import cmp_to_key
import pytest


def test_is_empty():
    assert is_empty([]) == True
    assert is_empty([1,2,3]) == False
    assert is_empty('') == True
    assert is_empty('hello') == False


@pytest.mark.parametrize(
    'text, expected', [('true', True), 
                       ('TRUE', True),
                       ('True', True),
                       ('1', True),
                       (1, True),
                       ('false', False),
                       ('False', False),
                       ('FALSE', False),
                       (0, False),
                       ([], False),
                       (1.0, False),
                       (0.0, False)]
)
def test_str_to_bool(text: str, expected: str|int):
    assert str_to_bool(text) == expected


@pytest.mark.parametrize(
    # '0' - equal, '-1' - less, '1' - greater
    # -1 if right is greater (left should be sorted before the right)
    # 1 if left is greater (left should be sorted after the right)
    'l, r, expected', [
        ('id-123', 'id-123', 0),
        ('id-123', 'id-124', -1), 
        ('id-1230', 'id-124', 1),
        ('id-123', 'ID-123', 0),
        ('id-05', 'ID-5', 0),
        ('cpp-12', 'TODO-1', -1),
        ('CPP-12', 'todo-1', -1),
        ('QA-12', 'cpp-18', 1),
    ]
)
def test_issue_comparator(l: str, r: str, expected: int):
    assert issue_id_comparator(l, r) == expected


@pytest.mark.parametrize(
    'id, expected', [
        ('id-123', ('id', 123)),
        ('TODO-011', ('todo', 11))
    ]
)
def test_issue_key(id: str, expected: tuple[str, int]):
    assert issue_id_to_key(id) == expected


def test_sort_issues_list():
    src = ['TODO-591', 'id-11276', 'QA-015', 'id-9839', 'cpp-18', 'QA-12']
    exp = ['cpp-18', 'id-9839', 'id-11276', 'QA-12', 'QA-015', 'TODO-591']
    assert sorted(src, key=issue_id_to_key) == exp
    assert sorted(src, key=cmp_to_key(issue_id_comparator)) == exp