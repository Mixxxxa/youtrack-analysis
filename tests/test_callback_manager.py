import pytest
from typing import Protocol, runtime_checkable
from unittest.mock import Mock

from youtrack.utils.callback_manager import CallbackManager


@runtime_checkable
class SimpleHandler(Protocol):
    def __call__(self, x: int, y: int) -> None: ...

@runtime_checkable
class DataProcessor(Protocol):
    def __call__(self, data: str, count: int = 1) -> None: ...

@runtime_checkable
class NoArgsHandler(Protocol):
    def __call__(self) -> None: ...

@runtime_checkable
class ReturningHandler(Protocol):
    def __call__(self, value: int) -> str: ...

# Невалидные Protocol'ы для тестирования ошибок
class NotRuntimeCheckable(Protocol):
    def __call__(self, x: int) -> None: ...

class NoCallMethod(Protocol):
    def process(self, x: int) -> None: ...

@pytest.fixture
def simple_callback_manager():
    """Менеджер коллбеков для простых handler'ов."""
    return CallbackManager(SimpleHandler)

@pytest.fixture
def data_callback_manager():
    """Менеджер коллбеков для обработки данных."""
    return CallbackManager(DataProcessor)

@pytest.fixture
def mock_simple_handler():
    """Mock handler с правильной сигнатурой."""
    handler = Mock(spec=SimpleHandler)
    handler.__call__ = Mock(return_value=None)
    return handler

@pytest.fixture
def real_simple_handlers():
    """Реальные handler'ы для тестирования."""
    def handler1(x: int, y: int) -> None:
        pass
    
    def handler2(x: int, y: int) -> None:
        pass
    
    def wrong_signature_handler(x: int) -> None:
        pass
    
    def wrong_type_handler(x: str, y: str) -> None:
        pass
    
    return {
        'handler1': handler1,
        'handler2': handler2,
        'wrong_signature': wrong_signature_handler,
        'wrong_type': wrong_type_handler
    }


class TestInitialization:
    """Тесты инициализации CallbackManager."""
    
    def test_valid_protocol_initialization(self):
        """Тест успешной инициализации с валидным Protocol."""
        manager = CallbackManager(SimpleHandler)
        assert manager._protocol_type == SimpleHandler
        assert len(manager) == 0
    

    def test_invalid_protocol_not_runtime_checkable(self):
        """Тест ошибки при инициализации с Protocol без @runtime_checkable."""
        with pytest.raises(TypeError, match="must be a @runtime_checkable Protocol"):
            CallbackManager(NotRuntimeCheckable)
    

    def test_invalid_protocol_no_call_method(self):
        """Тест ошибки при инициализации с Protocol без __call__."""
        with pytest.raises(TypeError, match="must be a @runtime_checkable Protocol"):
            CallbackManager(NoCallMethod)


# # === ТЕСТЫ ДОБАВЛЕНИЯ КОЛЛБЕКОВ ===

class TestAddingCallbacks:
    """Тесты добавления коллбеков."""
    
    def test_add_valid_callback(self, simple_callback_manager: CallbackManager, real_simple_handlers: dict[str, CallbackManager]):
        """Тест добавления валидного коллбека."""
        handler = real_simple_handlers['handler1']
        cb_manager = simple_callback_manager
        cb_manager += handler
        
        assert cb_manager is simple_callback_manager
        assert len(cb_manager) == 1
        assert handler in cb_manager
    

    def test_add_multiple_callbacks(self, simple_callback_manager: CallbackManager, real_simple_handlers: dict[str, CallbackManager]):
        """Тест добавления нескольких коллбеков."""
        handler1 = real_simple_handlers['handler1']
        handler2 = real_simple_handlers['handler2']
        
        simple_callback_manager += handler1
        simple_callback_manager += handler2
        
        assert len(simple_callback_manager) == 2
        assert handler1 in simple_callback_manager
        assert handler2 in simple_callback_manager
    

    def test_add_callback_wrong_signature(self, simple_callback_manager: CallbackManager, real_simple_handlers: dict[str, CallbackManager]):
        """Тест ошибки при добавлении коллбека с неправильной сигнатурой."""
        wrong_handler = real_simple_handlers['wrong_signature']
        
        with pytest.raises(TypeError, match="doesn't match expected"):
            simple_callback_manager += wrong_handler
    

    def test_add_callback_wrong_types(self, simple_callback_manager: CallbackManager, real_simple_handlers: dict[str, CallbackManager]):
        """Тест ошибки при добавлении коллбека с неправильными типами."""
        wrong_handler = real_simple_handlers['wrong_type']
        
        with pytest.raises(TypeError, match="doesn't match expected"):
            simple_callback_manager += wrong_handler
    
    def test_add_non_protocol_callback(self, simple_callback_manager: CallbackManager):
        """Тест ошибки при добавлении объекта, не реализующего Protocol."""
        non_callable = "not a callback"
        
        with pytest.raises(TypeError, match="must implement SimpleHandler"):
            simple_callback_manager += non_callable
    
    def test_add_duplicate_callback(self, simple_callback_manager: CallbackManager, real_simple_handlers: dict[str, CallbackManager]):
        """Тест ошибки при добавлении дублирующегося коллбека."""
        handler = real_simple_handlers['handler1']
        
        simple_callback_manager += handler
        
        with pytest.raises(ValueError, match="already registered"):
            simple_callback_manager += handler
    
    def test_add_callback_with_defaults(self, data_callback_manager: CallbackManager):
        """Тест добавления коллбека с параметрами по умолчанию."""
        def handler_with_defaults(data: str, count: int = 1) -> None:
            pass
        
        data_callback_manager += handler_with_defaults
        
        assert len(data_callback_manager) == 1


class TestCallingCallbacks:
    """Тесты вызова коллбеков."""
    
    def test_call_single_callback(self):
        """Тест вызова одного коллбека."""
        
        mock_handler = Mock()
        
        class CheckHandler(SimpleHandler):
            def my_callback(self, x: int, y: int) -> None:
                mock_handler(x,y)
        
        manager = CallbackManager(SimpleHandler)
        obj = CheckHandler()
        manager += obj.my_callback
        manager(10, 20)
        mock_handler.assert_called_once_with(10, 20)
    

    def test_call_multiple_callbacks_fifo_order(self):
        """Тест вызова нескольких коллбеков в порядке FIFO."""
        manager = CallbackManager(SimpleHandler)
        call_order = []
        
        def handler1(x: int, y: int) -> None:
            call_order.append('handler1')
        def handler2(x: int, y: int) -> None:
            call_order.append('handler2')
        def handler3(x: int, y: int) -> None:
            call_order.append('handler3')
        
        manager += handler1
        manager += handler2
        manager += handler3
        manager(1, 2)
        assert call_order == ['handler1', 'handler2', 'handler3']
    

    @pytest.mark.skip(reason="Not implemented yet")
    def test_call_with_wrong_argument_types(self, simple_callback_manager, real_simple_handlers):
        """Тест ошибки при вызове с неправильными типами аргументов."""
        handler = real_simple_handlers['handler1']
        simple_callback_manager += handler
        with pytest.raises(TypeError, match="expected type int.*got str"):
            simple_callback_manager("wrong", "types")
    

    @pytest.mark.skip(reason="Not implemented yet")
    def test_call_with_wrong_number_of_arguments(self, simple_callback_manager, real_simple_handlers):
        """Тест ошибки при вызове с неправильным количеством аргументов."""
        handler = real_simple_handlers['handler1']
        simple_callback_manager += handler
        
        with pytest.raises(TypeError, match="Invalid arguments"):
            simple_callback_manager(1)  # Недостаток аргументов
            
        with pytest.raises(TypeError, match="Invalid arguments"):
            simple_callback_manager(1, 2, 3)  # Слишком много аргументов
    

    @pytest.mark.skip(reason="Not implemented yet")
    def test_call_with_defaults(self, data_callback_manager):
        """Тест вызова с параметрами по умолчанию."""
        mock_handler = Mock()
        mock_handler.__call__ = Mock(return_value=None)
        
        data_callback_manager += mock_handler
        
        # Вызов без указания count (должен использовать значение по умолчанию)
        data_callback_manager("test")
        mock_handler.__call__.assert_called_once_with("test")
        
        mock_handler.__call__.reset_mock()
        
        # Вызов с явно указанным count
        data_callback_manager("test", 5)
        mock_handler.__call__.assert_called_once_with("test", 5)
    

    def test_call_empty_manager(self, simple_callback_manager):
        """Тест вызова менеджера без коллбеков."""
        # Не должно вызывать ошибок
        simple_callback_manager(1, 2)
    
    def test_callback_exception_propagation(self, simple_callback_manager):
        """Тест пробрасывания исключений из коллбеков."""
        def failing_handler(x: int, y: int) -> None:
            raise RuntimeError("Handler failed")
        
        simple_callback_manager += failing_handler
        
        with pytest.raises(RuntimeError, match="Handler failed"):
            simple_callback_manager(1, 2)
    
    def test_callback_exception_stops_execution(self, simple_callback_manager):
        """Тест что исключение в коллбеке останавливает выполнение остальных."""
        call_order = []
        
        def handler1(x: int, y: int) -> None:
            call_order.append('handler1')
        
        def failing_handler(x: int, y: int) -> None:
            call_order.append('failing')
            raise RuntimeError("Handler failed")
        
        def handler2(x: int, y: int) -> None:
            call_order.append('handler2')
        
        simple_callback_manager += handler1
        simple_callback_manager += failing_handler
        simple_callback_manager += handler2
        
        with pytest.raises(RuntimeError):
            simple_callback_manager(1, 2)
        
        assert call_order == ['handler1', 'failing']  # handler2 не должен вызываться


class TestUtilityMethods:
    """Тесты утилитарных методов."""
    
    def test_len_empty_manager(self, simple_callback_manager):
        """Тест len для пустого менеджера."""
        assert len(simple_callback_manager) == 0

    
    def test_len_with_callbacks(self, simple_callback_manager, real_simple_handlers):
        """Тест len с коллбеками."""
        simple_callback_manager += real_simple_handlers['handler1']
        assert len(simple_callback_manager) == 1
        simple_callback_manager += real_simple_handlers['handler2']
        assert len(simple_callback_manager) == 2

    
    def test_contains_existing_callback(self, simple_callback_manager, real_simple_handlers):
        """Тест __contains__ для существующего коллбека."""
        handler = real_simple_handlers['handler1']
        simple_callback_manager += handler
        assert handler in simple_callback_manager

    
    def test_contains_non_existing_callback(self, simple_callback_manager, real_simple_handlers):
        """Тест __contains__ для несуществующего коллбека."""
        handler = real_simple_handlers['handler1']
        assert handler not in simple_callback_manager

    
    def test_clear(self, simple_callback_manager, real_simple_handlers):
        """Тест метода clear."""
        simple_callback_manager += real_simple_handlers['handler1']
        simple_callback_manager += real_simple_handlers['handler2']
        assert len(simple_callback_manager) == 2
        simple_callback_manager.clear()
        assert len(simple_callback_manager) == 0
        assert real_simple_handlers['handler1'] not in simple_callback_manager
        assert real_simple_handlers['handler2'] not in simple_callback_manager


class TestIntegration:
    """Интеграционные тесты полного workflow."""
    
    def test_full_workflow(self):
        """Тест полного жизненного цикла менеджера коллбеков."""
        # Создаем менеджер
        manager = CallbackManager(SimpleHandler)
        
        # Создаем коллбеки
        results = []
        
        def handler1(x: int, y: int) -> None:
            results.append(f"h1:{x},{y}")
        
        def handler2(x: int, y: int) -> None:
            results.append(f"h2:{x},{y}")
        
        def handler3(x: int, y: int) -> None:
            results.append(f"h3:{x},{y}")
        
        # Добавляем коллбеки
        manager += handler1
        manager += handler2
        manager += handler3
        
        assert len(manager) == 3
        
        # Вызываем
        manager(10, 20)
        assert results == ["h1:10,20", "h2:10,20", "h3:10,20"]
        
        # Удаляем средний коллбек
        manager -= handler2
        assert len(manager) == 2
        
        # Вызываем снова
        results.clear()
        manager(30, 40)
        assert results == ["h1:30,40", "h3:30,40"]
        
        # Очищаем все
        manager.clear()
        assert len(manager) == 0
        
        # Вызов пустого менеджера
        results.clear()
        manager(50, 60)
        assert results == []
    

    def test_complex_callback_with_state(self):
        """Тест коллбека с состоянием."""
        manager = CallbackManager(SimpleHandler)
        
        class StatefulHandler:
            def __init__(self):
                self.calls = []
            
            def __call__(self, x: int, y: int) -> None:
                self.calls.append((x, y))
        
        handler = StatefulHandler()
        manager += handler
        
        manager(1, 2)
        manager(3, 4)
        
        assert handler.calls == [(1, 2), (3, 4)]


class TestEdgeCases:
    def test_callback_modifying_manager_during_execution(self):
        """Тест коллбека, который пытается изменить менеджер во время выполнения."""
        manager = CallbackManager(SimpleHandler)
        
        def self_removing_handler(x: int, y: int) -> None:
            # Попытка удалить себя во время выполнения
            # В реальном коде это может вызвать проблемы, но мы должны это обработать
            manager.clear()
        
        manager += self_removing_handler
        manager(1, 2)
    

    def test_signature_with_complex_types(self):
        """Тест с более сложными типами в сигнатуре."""
        from typing import List, Dict
        
        @runtime_checkable
        class ComplexHandler(Protocol):
            def __call__(self, data: List[str], mapping: Dict[str, int]) -> None: ...
        
        manager = CallbackManager(ComplexHandler)
        
        def handler(data: List[str], mapping: Dict[str, int]) -> None:
            pass
        
        manager += handler
        manager(["test"], {"key": 1})
