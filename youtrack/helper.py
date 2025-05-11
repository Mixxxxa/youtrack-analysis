import requests
import re
import typing as t
from .config import YouTrackConfig
from .entities import IssueInfo
from .utils import InvalidIssueIdError, yt_logger, is_empty
from .parser import IssueParser
from urllib.parse import urlparse,parse_qs

class ApiHelper:
    issue_re = re.compile(r'^id-\d{4,5}$')

    def __init__(self, config: YouTrackConfig):
        self.__config = config

    def __get_header(self) -> dict[str,str]:
        return {
            "Accept": "application/json",
            "Authorization": self.__config.api_key,
            "Content-type": "application/json",
            "Cache-Control": "no-cache"
        }
    
    def __request(self, url: str) -> t.Any:
        yt_logger.debug(f"Request: '{url}'")
        rsp = requests.get(f'{self.__config.api_url}/{url}', headers=self.__get_header())
        rsp.raise_for_status()
        return rsp.json()

    def is_valid_issue_id(self, id: str) -> bool:
        return self.issue_re.match(id)
    
    def extract_issue_id(self, text: str) -> str | None:
        # Try as ID
        if self.is_valid_issue_id(text):
            return text
        # Try as URL
        try:
            parts = urlparse(text)
            if parts.scheme != 'https':
                return None
            if parts.hostname is None or parts.hostname != self.__config.host:
                return None
            if parts.path is None or is_empty(parts.path):
                return None
            
            if parts.path.startswith('/youtrack/agiles/') and not is_empty(parts.query):
                query_parts = parse_qs(qs=parts.query)
                if 'issue' in query_parts and self.is_valid_issue_id(query_parts['issue'][0]):
                    return query_parts['issue'][0]
                
            if parts.path.startswith('/youtrack/issue/'):
                path_parts = [s for s in str.split(parts.path, sep='/') if not is_empty(s.strip())]
                if len(path_parts) > 2 and self.is_valid_issue_id(path_parts[2]):
                    return path_parts[2]
        except:
            pass
        return None

    def get_summary(self, id: str) -> IssueInfo:
        if (issue_id := self.extract_issue_id(id)) is None:
            raise InvalidIssueIdError(id=id)
        
        activities_categories: list[str] = [
            'CommentsCategory',
            'CustomFieldCategory',
            'IssueCreatedCategory',
            'IssueResolvedCategory',
            'WorkItemCategory',
            'TagsCategory'
        ]
        activities_fields: list[str] = [
            'id',
            'author(name,login)',
            'added(name,duration(minutes,presentation))',
            'removed(name,duration(minutes,presentation))',
            'timestamp',
            'target(id,text)',
            'targetMember',
            'authorGroup(id,name)',
            'field(presentation,name)'
        ]
        issue_summary_fields = [
            'idReadable',
            'summary',
            'created',
            'reporter(fullName)',
            'customFields(id,name,value(minutes,fullName,name))',
            'tags(id,color(background,foreground),name)',
            'comments(author(fullName),created,text)'
        ]
        issue_links_fields = [
            'id',
            'idReadable',
            'direction',
            'linkType(name,localizedName,sourceToTarget,targetToSource,directed,aggregation)',
            f'issues({",".join(issue_summary_fields)})'
        ]
        issue_summary_fields.append(f'links({",".join(issue_links_fields)})')

        activities_url = f"issues/{issue_id}/activities?fields={','.join(activities_fields)}&categories={','.join(activities_categories)}"
        custom_fields_url = f'issues/{issue_id}?fields={",".join(issue_summary_fields)}'
        assert custom_fields_url.count('links(') == 1, 'Found recursion in custom fields request'

        parser = IssueParser(self.__config.custom_fields)
        parser.parse_custom_fields(self.__request(url=custom_fields_url))
        parser.parse_activities(self.__request(url=activities_url))
        return parser.get_result()
    