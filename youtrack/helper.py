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


from asyncio import sleep, Semaphore
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from starlette import status
from yarl import URL
import aiohttp
import asyncio
import random
import typing as t

from .instance import YouTrackInstanceConfig
from .entities import IssueInfo, ProjectExt, CustomFields, Version
from .parser import IssueParser
from .utils import yt_logger
from .utils.anomalies import AnomaliesDetector
from .utils.timestamp import Timestamp
from .utils.exceptions import InvalidIssueIdError, TooMuchIssuesInBatchError, UnableToCountIssues
from .utils.others import is_valid_issue_id, extract_issue_id_from_url


def _is_retriable(exc: BaseException) -> bool:
    """
    Определяем, какие ошибки считаем временными и будет ли повтор попытки.
    """
    if isinstance(exc, asyncio.TimeoutError):
        return True
    
    if isinstance(exc, aiohttp.ClientResponseError):
        code = exc.status
        if code == status.HTTP_429_TOO_MANY_REQUESTS or 500 <= code < 600:
            return True

    if isinstance(exc, aiohttp.ClientError):
        # Любая сетевая ошибка aiohttp (соединение, DNS, reset и т.п.)
        return True

    # Базовые сетевые ошибки на уровне сокетов
    if isinstance(exc, (ConnectionError, OSError)):
        return True

    return False


class YouTrackHelper:
    BATCH_SIZE = 50
    MAX_ISSUE_COUNT = 500
    MAX_RECONNECTION_ATTEMPTS = 3
    CONNECTION_TIMEOUT_SEC = 10


    def __init__(self, instance_url: str, api_key: str):
        self.__instance_url = instance_url
        self.__api_key = api_key


    def __get_header(self) -> dict[str,str]:
        return {
            "Accept": "application/json",
            "Authorization": self.__api_key,
            "Content-type": "application/json",
            "Cache-Control": "no-cache"
        }
    

    async def __fetch_json(self, session: aiohttp.ClientSession, url: URL, backoff_schedule: t.Sequence[float] = (0.5, 1.0, 2.0)) -> t.Any:
        assert len(backoff_schedule) == self.MAX_RECONNECTION_ATTEMPTS, 'backoff size must be equal to MAX_RECONNECTION_ATTEMPTS'
        for attempt in range(1, self.MAX_RECONNECTION_ATTEMPTS+1):
            try:
                async with asyncio.timeout(self.CONNECTION_TIMEOUT_SEC):
                    async with session.get(url, headers=self.__get_header()) as response:
                        response.raise_for_status()
                        return await response.json()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if not _is_retriable(e) or attempt == self.MAX_RECONNECTION_ATTEMPTS:
                    raise
                # Экспоненциальный бэкофф с фулл-джиттером
                base = backoff_schedule[attempt - 1]
                # множитель 0..1 (фулл-джиттер)
                delay = random.uniform(0, base)
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
        raise RuntimeError(f'Something went wrong while fetching data from backend')


    async def __fetch_json_ex(self, session: aiohttp.ClientSession, fetch_sem: Semaphore, url: URL, backoff_schedule: t.Sequence[float] = (0.5, 1.0, 2.0)) -> t.Any:
        """
        Получает данные с ограничением на конкурентность (fetch_sem),
        повторами и таймаутом на каждую попытку.
        Fail-fast в случае фатальной ошибки, иначе пытается до `YouTrackHelper.MAX_RECONNECTION_ATTEMPTS` раз.
        """
        async with fetch_sem:
            return self.__fetch_json_ex(session=session, 
                                        url=url, 
                                        backoff_schedule=backoff_schedule)
        

    def extract_issue_id(self, text: str) -> str | None:
        # Try as ID
        if is_valid_issue_id(text):
            return text
        # Try as URL
        return extract_issue_id_from_url(text, self.__instance_url)
    

    async def get_summary(self, id: str, anomaly_detector: AnomaliesDetector, custom_fields: CustomFields) -> IssueInfo:
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
            'project(id,name,shortName)',
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

        custom_fields_query = {
            'fields': ",".join(issue_summary_fields)
        }
        activities_query = {
            'fields': ','.join(activities_fields),
            'categories': ','.join(activities_categories)
        }

        issues_endpoint = '/youtrack/api/issues'
        urls = [
            # Custom fields
            URL.build(scheme='https', 
                      host=self.__instance_url, 
                      path=f'{issues_endpoint}/{issue_id}',
                      query=custom_fields_query),
            # Activities
            URL.build(scheme='https', 
                      host=self.__instance_url, 
                      path=f'{issues_endpoint}/{issue_id}/activities',
                      query=activities_query)
        ]

        async with aiohttp.ClientSession() as session:
            tasks = [self.__fetch_json(session, url) for url in urls]
            results = await asyncio.gather(*tasks)

        parser = IssueParser(custom_fields)
        parser.cb_pause_added += anomaly_detector.on_pause_added
        parser.cb_tag_added += anomaly_detector.on_tag_added
        parser.cb_work_added += anomaly_detector.on_work_added
        parser.cb_assignee_changed += anomaly_detector.on_assignee_changed
        parser.cb_scope_changed += anomaly_detector.on_scope_changed
        parser.cb_state_changed += anomaly_detector.on_state_changed
        parser.cb_parsing_finished += anomaly_detector.on_parsing_finished

        parser.parse_custom_fields(results[0])
        parser.parse_activities(results[1])
        return parser.get_result()
    

    async def get_raw_issues_by_query(self, query: str, fields: list[str]) -> list[dict[str,t.Any]]:
        async with aiohttp.ClientSession() as session:
            # Узнаем сколько вообще доступно issue для этого query
            total_issue_count = await self.get_issue_count(query=query, session=session)
            if total_issue_count is None:
                yt_logger.error(f'Unable to get issues count for query: {query}')
                raise UnableToCountIssues()
            elif total_issue_count == 0:
                return dict()
            elif total_issue_count > self.MAX_ISSUE_COUNT:
                yt_logger.error(f'Tried to get more than {self.MAX_ISSUE_COUNT} issues ({total_issue_count}) with query: {query}')
                raise TooMuchIssuesInBatchError(count=total_issue_count)
            
            urls: list[URL] = []
            for i in range(0, total_issue_count, YouTrackHelper.BATCH_SIZE):
                urls.append(URL.build(scheme='https', 
                                      host=self.__instance_url, 
                                      path=f'/youtrack/api/issues',
                                      query={ 
                                          'query': query, 
                                          'fields': ','.join(fields),
                                          '$skip': i,
                                          '$top': YouTrackHelper.BATCH_SIZE
                                      }))
            tasks = [self.__fetch_json(session, url) for url in urls]
            data = await asyncio.gather(*tasks)
            return list(chain.from_iterable(data))
    

    async def get_issue_count(self, query: str, session: aiohttp.ClientSession) -> int|None:
        url = URL.build(scheme='https', 
                        host=self.__instance_url, 
                        path=f'/youtrack/api/issuesGetter/count',
                        query={ 'fields': 'count' })
        
        # From docs:
        # If this number equals -1, it means that YouTrack hasn't finished counting the issues yet. 
        # Wait for a bit and repeat the request.
        for i in range(self.MAX_RECONNECTION_ATTEMPTS):
            async with session.post(url, headers=self.__get_header(), json={ 'query': query }) as response:
                response.raise_for_status()
                res: dict[str, t.Any] = await response.json()
                count = res.get('count', None)

                if count is not None and count != -1:
                    return count
                
                if i < (self.MAX_RECONNECTION_ATTEMPTS - 1):
                    await sleep(0.2 * i)
        return None
    

    async def get_issue_activities(self, session: aiohttp.ClientSession, issue_id: str, fields: list[str], categories: list[str]) -> t.Any:
        url = URL.build(scheme='https', 
                        host=self.__instance_url, 
                        path=f'/youtrack/api/issues/{issue_id}/activities',
                        query={ 
                            'fields': ','.join(fields),
                            'categories': ','.join(categories) 
                        })
        return await self.__fetch_json(session, url) #TODO PZDC
    

    def get_issues_search_url(self, query: str) -> URL:
        return URL.build(scheme='https', 
                         host=self.__instance_url, 
                         path=f'/youtrack/issues',
                         query={ 'q': query })
    

    async def get_instance_settings(self) -> YouTrackInstanceConfig:
        """
        Получение настроек от инстанса YouTrack
        """
        async def get_all_projects(session: aiohttp.ClientSession) -> t.Any:
            url = URL.build(scheme='https', 
                host=self.__instance_url, 
                path=f'/youtrack/api/admin/projects',
                query={ 'fields': 'id,name,shortName' }
            )
            return await self.__fetch_json(session=session, url=url)
        
        async def get_all_custom_fields(session: aiohttp.ClientSession) -> t.Any:
            url = URL.build(scheme='https', 
                host=self.__instance_url, 
                path=f'/youtrack/api/admin/customFieldSettings/customFields',
                query={'fields': 'id,name,instances(id,project(id,name))'}
            )
            return await self.__fetch_json(session=session, url=url)
        
        @dataclass
        class CustomFieldInstance:
            project_id: str
            instance_id: str

        # key: component name, value: CustomFieldInstance
        def extract_all_custom_field_instances(data: t.Any) -> dict[str,list[CustomFieldInstance]]:
            ret = defaultdict(list)
            for field in data:
                if field['instances']:
                    for instance in field['instances']:
                        ret[field['name']].append(CustomFieldInstance(project_id=instance['project']['id'], 
                                                                      instance_id=instance['id']))
            return ret

        async def get_all_possible_values(session: aiohttp.ClientSession, instances: list[CustomFieldInstance]) -> dict[str, list[str]]:
            urls = [URL.build(scheme='https', 
                              host=self.__instance_url, 
                              path=f'/youtrack/api/admin/projects/{i.project_id}/customFields/{i.instance_id}',
                              query={'fields': 'bundle(values(name)),canBeEmpty,emptyFieldText'}) for i in instances]
            tasks = [self.__fetch_json(session, url) for url in urls]
            data = await asyncio.gather(*tasks)
            return { i[0].project_id: sorted([j['name'] for j in i[1]['bundle']['values']]) for i in zip(instances, data) }
        
        async def get_versions(session: aiohttp.ClientSession, instances: list[CustomFieldInstance]) -> list[Version]:
            urls = [URL.build(scheme='https', 
                              host=self.__instance_url, 
                              path=f'/youtrack/api/admin/projects/{i.project_id}/customFields/{i.instance_id}',
                              query={'fields': 'bundle(values(name,archived,startDate,releaseDate))'}) for i in instances]
            tasks = [self.__fetch_json(session, url) for url in urls]
            data = await asyncio.gather(*tasks)
            ret = list()
            # TODO Diag gaps
            for instance in data:
                for value in instance['bundle']['values']:
                    if value['archived'] is True:
                        continue
                    ret.append(Version(name=value['name'], 
                                       begin=Timestamp.from_yt(int(value['startDate'])), 
                                       end=Timestamp.from_yt(int(value['releaseDate']))))
            return ret
        
        # Если default нет, то ничего не возвращаем для проекта
        async def get_default_values(session: aiohttp.ClientSession, instances: list[CustomFieldInstance]) -> dict[str, str]:
            urls = [URL.build(scheme='https', 
                              host=self.__instance_url, 
                              path=f'/youtrack/api/admin/projects/{i.project_id}/customFields/{i.instance_id}',
                              query={'fields': 'canBeEmpty,emptyFieldText'}) for i in instances]
            tasks = [self.__fetch_json(session, url) for url in urls]
            data = await asyncio.gather(*tasks)
            ret = dict()
            for i in zip(instances, data):
                if i[1]['emptyFieldText']:
                    ret[i[0].project_id] = i[1]['emptyFieldText']
            return ret
        
        async with aiohttp.ClientSession() as session:
            projects = await get_all_projects(session=session)
            custom_fields = await get_all_custom_fields(session=session)
            custom_field_instances = extract_all_custom_field_instances(custom_fields)
            
            if not 'Component' in custom_field_instances.keys() or not 'Scope' in custom_field_instances.keys():
                raise RuntimeError('Unable to load projects information (custom fields Component and Scope)')

            component_info = await get_all_possible_values(session=session, instances=custom_field_instances['Component'])
            versions_info = await get_versions(session=session, instances=custom_field_instances['Release cycle'])

            projects_ret: dict[str, ProjectExt] = dict()
            for i in projects:
                projects_ret[i['shortName']] = ProjectExt(short_name=i['shortName'], 
                                                          name=i['name'], 
                                                          id=i['id'],
                                                          components=component_info.get(i['id'], []))
            return YouTrackInstanceConfig(projects=projects_ret, versions=versions_info)
