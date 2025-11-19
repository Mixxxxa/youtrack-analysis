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


from concurrent.futures import ThreadPoolExecutor
import asyncio
import pytest
import threading
import time

from ..utils.once import once


def test_once_sync_basic_same_result_and_single_execution():
    calls = 0

    @once()
    def add(a, b):
        nonlocal calls
        calls += 1
        return a + b

    assert add(1, 2) == 3
    # последующие вызовы игнорируют аргументы и возвращают первый результат
    assert add(100, 200) == 3
    assert calls == 1


def test_once_sync_returns_none_cached():
    calls = 0

    @once()
    def get_none():
        nonlocal calls
        calls += 1
        return None

    assert get_none() is None
    assert get_none() is None
    assert calls == 1


def test_once_sync_threaded_concurrency_only_once():
    calls = 0
    calls_lock = threading.Lock()

    @once()
    def work(x):
        nonlocal calls
        # эмулируем тяжёлую работу, чтобы повысить шанс гонки
        time.sleep(0.1)
        with calls_lock:
            calls += 1
        # Возвращаем вход — в итоге все потоки получат одно и то же значение:
        # значение из самого первого вызова.
        return x

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(work, i) for i in range(16)]
        results = [f.result(timeout=3) for f in futs]

    # Все результаты идентичны (значение первого, кто успел)
    assert len(set(results)) == 1
    # Тело функции выполнилось ровно один раз
    assert calls == 1


@pytest.mark.asyncio
async def test_once_async_basic_same_result_and_single_execution():
    calls = 0

    @once()
    async def add_async(a, b):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return a + b

    assert await add_async(1, 2) == 3
    assert await add_async(100, 200) == 3
    assert calls == 1


@pytest.mark.asyncio
async def test_once_async_concurrent_tasks_only_once():
    calls = 0

    @once()
    async def work_async(x):
        nonlocal calls
        # эмулируем тяжёлую работу, чтобы задачи зашли параллельно
        await asyncio.sleep(0.1)
        calls += 1
        return x

    # Запускаем пачку конкурентных вызовов
    tasks = [asyncio.create_task(work_async(i)) for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(set(results)) == 1  # все получили результат самого первого вызова
    assert calls == 1              # вычисление было только одно


def test_once_does_not_cache_exceptions_sync():
    calls = 0
    should_fail_first = True

    @once()
    def flaky():
        nonlocal calls, should_fail_first
        calls += 1
        if should_fail_first:
            should_fail_first = False
            raise RuntimeError("boom")
        return 42

    # первый вызов падает
    with pytest.raises(RuntimeError):
        flaky()

    # второй — успешный, т.к. исключения не кэшируются
    assert flaky() == 42
    assert calls == 2


def test_once_preserves_function_metadata():
    @once()
    def my_func():
        """Docstring here"""
        return 1

    assert my_func.__name__ == "my_func"
    assert my_func.__doc__ == "Docstring here"
    # благодаря @wraps должен быть __wrapped__
    assert hasattr(my_func, "__wrapped__")
