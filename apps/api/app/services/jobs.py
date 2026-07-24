from fastapi import BackgroundTasks

from ..config import get_settings
from .reporting import complete_report


def enqueue_report(report_id: str, background: BackgroundTasks) -> None:
    settings = get_settings()
    if settings.redis_url:
        from redis import Redis
        from rq import Queue, Retry

        queue = Queue("reports", connection=Redis.from_url(settings.redis_url))
        queue.enqueue(
            "app.services.reporting.complete_report",
            report_id,
            job_timeout=300,
            result_ttl=86400,
            failure_ttl=604800,
            retry=Retry(max=3, interval=[10, 60, 300]),
        )
        return
    background.add_task(complete_report, report_id)
