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


from functools import wraps
import threading
import inspect
import asyncio


def once():
    def deco(func):
        SENTINEL = object()
        value = SENTINEL

        if inspect.iscoroutinefunction(func):
            lock = asyncio.Lock()

            @wraps(func)
            async def wrapper(*args, **kwargs):
                nonlocal value
                if value is not SENTINEL:
                    return value
                async with lock:
                    if value is SENTINEL:
                        value = await func(*args, **kwargs)
                return value
        else:
            lock = threading.Lock()

            @wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal value
                if value is not SENTINEL:
                    return value
                with lock:
                    if value is SENTINEL:
                        value = func(*args, **kwargs)
                return value

        return wrapper
    return deco
