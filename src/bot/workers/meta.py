from abc import ABCMeta
from inspect import isabstract
from typing import Any

from bot.core.celery import celery_app


class WorkerMeta(ABCMeta):
    """Register concrete worker classes with Celery."""

    def __new__(
        mcls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> type:
        cls = super().__new__(mcls, name, bases, namespace)
        if not isabstract(cls):
            celery_app.register_task(cls())
        return cls
