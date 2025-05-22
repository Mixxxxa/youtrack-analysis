from youtrack import YouTrackConfig, ApiHelper
import pytest


@pytest.fixture
def config_for_url_test():
    return YouTrackConfig(host='my-yt.myjetbrains.com',
                          api_key='',
                          support_person='')


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
def test_parse_issue_id_from_request(config_for_url_test: YouTrackConfig, req: str, expected: str | None):
    a = ApiHelper(config_for_url_test)
    assert a.extract_issue_id(req) == expected