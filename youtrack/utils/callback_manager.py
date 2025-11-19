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


from typing import TypeVar, Generic, List, Type, Any, Self
import inspect


P = TypeVar('P')


class CallbackManager(Generic[P]):
    """
    Менеджер callback-функций с типизацией и проверкой сигнатур

    Пример использования:

    ```
@runtime_checkable
class ButtonClickHandler(Protocol):
    def __call__(self, x: int, y: int) -> None: ...

def handler1(x: int, y: int) -> None:
    print(f"Handler 1: {x}, {y}")

callbacks = CallbackManager(ButtonClickHandler)
callbacks += handler1
callbacks(100, 200)  # Вызовет handler с проверкой типов аргументов
    ```
    """

    def __init__(self, protocol_type: Type[P]):
        has_all_attrs = all(hasattr(protocol_type, attr) for attr in ['_is_protocol', '__call__', '_is_runtime_protocol'])
        is_ok = has_all_attrs and getattr(protocol_type, '_is_runtime_protocol')
        if not is_ok:
            raise TypeError("protocol_type must be a @runtime_checkable Protocol with __call__ method")

        self._protocol_type = protocol_type
        self._callbacks: List[P] = []
        self._expected_signature = inspect.signature(protocol_type.__call__)

    def append(self, callback: P) -> None:
        self.__iadd__(callback=callback)

    def __iadd__(self, callback: P) -> Self:
        if not isinstance(callback, self._protocol_type):
            raise TypeError(f"Callback must implement {self._protocol_type.__name__}")
        if any(existing is callback for existing in self._callbacks):
            raise ValueError("Callback is already registered")
        self._validate_callback_signature(callback)
        self._callbacks.append(callback)
        return self

    def __isub__(self, callback: P) -> Self:
        """Удаляет коллбек."""
        self._callbacks = [cb for cb in self._callbacks if cb is not callback]
        return self

    def _validate_callback_signature(self, callback: Any) -> None:
        """Проверяет соответствие сигнатуры коллбека ожидаемой."""
        try:
            callback_signature = inspect.signature(callback)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot inspect callback signature: {e}")

        if not self._signatures_match(self._expected_signature, callback_signature):
            raise TypeError(
                f"Callback signature {callback_signature} doesn't match expected {self._expected_signature}"
            )

    def _signatures_match(self, expected: inspect.Signature, actual: inspect.Signature) -> bool:
        """Сравнивает две сигнатуры функций."""
        expected_params = self._get_params_without_self(expected)
        actual_params = self._get_params_without_self(actual)

        # Проверяем количество параметров
        if len(expected_params) != len(actual_params):
            return False

        # Проверяем каждый параметр
        for exp_param, act_param in zip(expected_params, actual_params):
            is_match = (exp_param.annotation == act_param.annotation and
                        exp_param.default == act_param.default and
                        exp_param.kind == act_param.kind)
            if not is_match:
                return False

        # Проверяем возвращаемый тип
        return expected.return_annotation == actual.return_annotation

    def _get_params_without_self(self, signature: inspect.Signature) -> List[inspect.Parameter]:
        """Возвращает параметры сигнатуры, исключая 'self'."""
        params = list(signature.parameters.values())
        if params and params[0].name == 'self':
            params = params[1:]
        return params

    def __call__(self, *args, **kwargs) -> None:
        """
        Вызывает все коллбеки в порядке добавления (FIFO).
        Сигнатура этого метода соответствует сигнатуре Protocol.__call__
        """
        # Проверяем аргументы перед вызовом коллбеков (выкл. т.к. садит перф)
        # self._validate_call_arguments(*args, **kwargs)

        # Вызываем все коллбеки в порядке добавления
        for callback in self._callbacks:
            # Исключения пробрасываются сразу
            callback(*args, **kwargs)

    # Нужно решить проблемы с производительностью и аргументом self
    # def _validate_call_arguments(self, *args, **kwargs) -> None:
    #     """Проверяет соответствие переданных аргументов ожидаемой сигнатуре."""
    #     try:
    #         # Создаем bound arguments для проверки
    #         bound_args = self._expected_signature.bind(*args, **kwargs)
    #         bound_args.apply_defaults()
    #     except TypeError as e:
    #         raise TypeError(f"Invalid arguments for callback: {e}")

    def clear(self) -> None:
        """Удаляет все коллбеки."""
        self._callbacks.clear()

    def __len__(self) -> int:
        """Возвращает количество зарегистрированных коллбеков."""
        return len(self._callbacks)

    def __contains__(self, callback: Any) -> bool:
        """Проверяет, зарегистрирован ли коллбек."""
        return any(existing is callback for existing in self._callbacks)
