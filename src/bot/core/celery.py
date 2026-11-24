from celery import signals
from celery.app.base import Celery
from celery.worker.worker import WorkController

from bot.core import config

celery_app = Celery(
    "foxbot",
    broker=config.settings.CELERY_BROKER_URL.get_secret_value().strip() or None,
    include=["bot.workers.telegram"],
    broker_connection_retry_on_startup=False,
)


@signals.worker_init.connect
def require_broker(sender: WorkController, **kwargs: object) -> None:
    if sender.app is celery_app and not celery_app.conf.broker_read_url:
        raise SystemExit(
            "FoxBot needs CELERY_BROKER_URL to start a queue worker. "
            "For Telegram monitoring, run uv run bot telegram-monitor.",
        )
