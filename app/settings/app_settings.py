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

from typing import Annotated, Tuple, Type
from pydantic import BaseModel, AfterValidator, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, JsonConfigSettingsSource
from pathlib import Path

from ..validators import api_key_validator, host_validator, iso8601_date_validator
from youtrack.utils.duration import Duration
from youtrack.entities import CustomFields


class CustomFieldsDefaultValues(BaseModel):
    scope: Duration


class ProjectSettings(BaseModel):
    default_values: CustomFieldsDefaultValues


class DatePreset(BaseModel):
    name: str
    description: str
    begin: Annotated[str, AfterValidator(iso8601_date_validator)]
    end: Annotated[str, AfterValidator(iso8601_date_validator)]


class AppSettings(BaseSettings):
    host: Annotated[str, AfterValidator(host_validator)]
    api_key: Annotated[str, AfterValidator(api_key_validator), Field(repr=False)]  # hide field from output
    support_person: str
    debug: bool = False
    custom_fields: CustomFields = CustomFields.default_config()  # какие поля брать при парсинге
    date_presets: list[DatePreset] = Field(default_factory=list)
    projects: dict[str, ProjectSettings] = Field(default_factory=dict)  # настроики по проектам

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls, json_file=Path(__file__).parent.parent.parent / 'instance.json'),
            env_settings
        )

    @property
    def api_url(self) -> str:
        return f'https://{self.host}/youtrack/api'

    def get_issue_url(self, issue_id: str) -> str:
        return f'https://{self.host}/youtrack/issue/{issue_id}'
