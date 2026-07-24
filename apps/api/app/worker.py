from redis import Redis
from rq import Queue, Worker

from .config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("Worker 需要 ABA_REDIS_URL")
    connection = Redis.from_url(settings.redis_url)
    worker = Worker([Queue("reports", connection=connection)], connection=connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
