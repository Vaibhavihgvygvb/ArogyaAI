from app.ai.memory.manager import InMemoryMemoryManager
from app.ai.interfaces.memory_manager import MemoryManager


_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = InMemoryMemoryManager()
    return _manager


def set_memory_manager(manager: MemoryManager) -> None:
    global _manager
    _manager = manager


def reset_memory_manager() -> None:
    global _manager
    _manager = None
