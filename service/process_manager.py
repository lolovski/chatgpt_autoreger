import asyncio
import logging

logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(self):
        self.tasks = {}

    def start(self, name: str, coro):
        if name in self.tasks:
            raise RuntimeError(f"Процесс {name} уже выполняется")
        task = asyncio.create_task(coro, name=name)
        self.tasks[name] = task
        logger.info(f"[ProcessManager] Запущен процесс {name}")
        return task

    def stop(self, name: str):
        task = self.tasks.get(name)
        if task and not task.done():
            task.cancel()
            logger.warning(f"[ProcessManager] Процесс {name} остановлен вручную")
        self.tasks.pop(name, None)

    def list_running(self):
        return [name for name, t in self.tasks.items() if not t.done()]

process_manager = ProcessManager()
