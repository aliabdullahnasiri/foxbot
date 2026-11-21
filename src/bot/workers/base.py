import asyncio
from abc import ABC, abstractmethod

from celery import Task

from bot.workers.meta import WorkerMeta


class BaseWorker(ABC, Task, metaclass=WorkerMeta):
    """Run each Celery task's async implementation on its own event loop."""

    abstract = True

    def run(self) -> None:
        asyncio.run(self._run())

    @abstractmethod
    async def _run(self) -> None: ...
