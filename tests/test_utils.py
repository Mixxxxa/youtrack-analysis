from youtrack import is_empty, str_to_bool
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
