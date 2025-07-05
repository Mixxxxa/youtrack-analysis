from dataclasses import dataclass
from .entities import CustomField
from .utils import str_to_bool, is_empty
from pathlib import Path
import json


@dataclass
class CustomFields:
    state: CustomField
    assignee: CustomField
    scope: CustomField
    spent_time: CustomField
    component: CustomField

    @staticmethod
    def default_config() -> 'CustomFields':
        return CustomFields(
            state=CustomField(id='110-33', name='State'),
            assignee=CustomField(id='111-7', name='Assignee'),
            scope=CustomField(id='116-7', name='Scope'),
            spent_time=CustomField(id='116-6', name='Spent time'),
            component=CustomField(id='110-32', name='Component')
        )


class YouTrackConfig:
    def __init__(self, host: str, api_key: str, support_person: str, port: int = 8080, debug: bool = False, custom_fields: CustomFields = CustomFields.default_config()):
        self.host = host.strip().lower()
        if self.host.startswith('https://') or self.host.startswith('http://'):
            raise RuntimeError(f"Host should contain only host-name. Example: 'myhost.myjetbrains.com'")
        self.port = port
        self.api_key = api_key
        self.debug = debug
        self.support_person = support_person
        self.custom_fields = custom_fields

    @staticmethod
    def from_file(filepath: Path):
        try:
            content = filepath.read_text(encoding='utf-8').strip()
            if is_empty(content):
                raise RuntimeError(f"Unable to parse configuration. File is empty: '{filepath}'")
            data: dict[str, str] = json.loads(content)
            return YouTrackConfig(host=data['host'],
                                  port=int(data.get('port', '8080')),
                                  api_key=data['api-key'],
                                  debug=str_to_bool(data.get('debug', 'False')),
                                  support_person=data['support-person'])
        except IOError as e:
            raise RuntimeError(f"Unable to read configuration file '{filepath}'")
        except KeyError as e:
            raise RuntimeError(f"Required congifuration field '{e.args[0]}' was not found")

    @property
    def api_url(self) -> str:
        return f'https://{self.host}/youtrack/api'
    
    def get_issue_url(self, issue_id: str) -> str:
        return f'https://{self.host}/youtrack/issue/{issue_id}'