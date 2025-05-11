from youtrack import YouTrackConfig
import pytest
import pathlib
import json


def write_json(file_path: pathlib.Path, obj) -> pathlib.Path:
    file_path.write_text(data=json.dumps(obj) if obj is not None else '', encoding='utf-8')
    return file_path


@pytest.mark.parametrize(
    'host, expected', [('127.0.0.1:80', '127.0.0.1:80'), 
                      ('test.myjetbrains.com', 'test.myjetbrains.com')]
)
def test_parse_url(host: str, expected: str):
    a = YouTrackConfig(host=host,
                       api_key='',
                       support_person='')
    assert a.host == expected


@pytest.mark.parametrize(
    'host', ['http://test.myjetbrains.com', 'https://test.myjetbrains.com']
)
def test_parse_bad_url(host: str):
    with pytest.raises(RuntimeError):
        YouTrackConfig(host=host,
                       api_key='',
                       support_person='')

def test_load_from_file_minimal(tmp_path: pathlib.Path):
    content = """
{
    "host": "my_yt.myjetbrains.com",
    "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
    "support-person": "John Doe"
}
"""
    file = tmp_path.joinpath('test_load_from_file_minimal.conf')
    file.write_text(content, encoding='utf-8')
    val = YouTrackConfig.from_file(file)
    assert val.host == "my_yt.myjetbrains.com"
    assert val.api_key == "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP"
    assert val.support_person == "John Doe"
    assert val.debug == False
    assert val.port == 8080


def test_load_from_non_exist_file(tmp_path: pathlib.Path):
    with pytest.raises(RuntimeError, match=r"Unable to read configuration file '.*?\.conf'"):
        YouTrackConfig.from_file(tmp_path.joinpath('unknown_file.conf'))


def test_load_from_file_minimal(tmp_path: pathlib.Path):
    with pytest.raises(RuntimeError, match=r"Unable to parse configuration. File is empty: '.*?\.conf'"):
        empty_file = write_json(tmp_path.joinpath('empty_file.conf'), None)
        YouTrackConfig.from_file(empty_file)

    with pytest.raises(RuntimeError, match=r"Required congifuration field 'host' was not found"):
        empty_file = write_json(tmp_path.joinpath('empty_file.conf'), {})
        YouTrackConfig.from_file(empty_file)

    with pytest.raises(RuntimeError, match=r"Required congifuration field 'api-key' was not found"):
        only_host = write_json(tmp_path.joinpath('only_host.conf'), {'host': 'lol'})
        YouTrackConfig.from_file(only_host)

    with pytest.raises(RuntimeError, match=r"Required congifuration field 'support-person' was not found"):
        host_and_key = write_json(tmp_path.joinpath('host_and_key.conf'), {'host': 'lol', 'api-key': 'kek'})
        YouTrackConfig.from_file(host_and_key)

    minimal_content = {
        "host": "my_yt.myjetbrains.com",
        "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
        "support-person": "John Doe"
    }
    val = YouTrackConfig.from_file(write_json(tmp_path.joinpath('min.conf'), minimal_content))
    assert val.host == "my_yt.myjetbrains.com"
    assert val.api_key == "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP"
    assert val.support_person == "John Doe"
    assert val.debug == False
    assert val.port == 8080
