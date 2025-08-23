import asyncio
import logging
from typing import Coroutine, Any, Dict, List

logger = logging.getLogger(__name__)


class ProcessManager:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}

    def start(self, name: str, coro: Coroutine) -> asyncio.Task:
        """Запуск нового процесса"""
        if name in self.tasks and not self.tasks[name].done():
            raise RuntimeError(f"Процесс {name} уже запущен")

        task = asyncio.create_task(coro, name=name)
        self.tasks[name] = task

        def _done_callback(t: asyncio.Task):
            try:
                result = t.result()
                logger.info(f"[ProcessManager] {name} завершён. Результат: {result}")
            except Exception as e:
                logger.error(f"[ProcessManager] {name} упал: {e}", exc_info=True)

        task.add_done_callback(_done_callback)
        return task

    async def result(self, name: str) -> Any:
        """Ждём результата процесса"""
        task = self.tasks.get(name)
        if not task:
            raise RuntimeError(f"Нет процесса {name}")
        return await task

    def stop(self, name: str):
        """Отмена задачи"""
        task = self.tasks.get(name)
        if task and not task.done():
            task.cancel()
            logger.warning(f"[ProcessManager] {name} отменён")

    def is_running(self, name: str) -> bool:
        """Проверка, запущен ли процесс"""
        task = self.tasks.get(name)
        return task is not None and not task.done()

    def list_running(self) -> List[str]:
        """Список активных процессов"""
        return [name for name, t in self.tasks.items() if not t.done()]


process_manager = ProcessManager()
