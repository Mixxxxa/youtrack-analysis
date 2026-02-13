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


from .app_settings import AppSettings
from youtrack.instance import YouTrackInstanceConfig
from dataclasses import dataclass


@dataclass
class Settings:
    app_config: AppSettings
    yt_config: YouTrackInstanceConfig

    def Validate(self) -> None:
        # Check values in virtual components by projects
        for project_short_name, project_info in self.app_config.projects.items():
            instance_project_config = self.yt_config.projects.get(project_short_name)
            if instance_project_config:
                project_components = set(instance_project_config.components)
                for i in project_info.virtual_components:
                    # Virtual component can't use the real component name
                    if i.name in project_components:
                        raise RuntimeError(f"Virtual component '{i.name}' can't be used because there is the same real component")
                    # All values in virtual group should really exist
                    unknown_components = set(i.values) - project_components
                    if len(unknown_components):
                        raise RuntimeError(f"Virtual components {unknown_components} cannot be used in the '{i.name}' group, as they are not present in project '{project_short_name}'")
